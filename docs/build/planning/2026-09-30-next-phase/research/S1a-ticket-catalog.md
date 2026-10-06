# S1a — Master ticket catalog

> **Row:** S1a (META_PLAN §6.S), S, depends on all design rows. **Authored:** 2026-09-30T23:30:40Z – 2026-10-01T00:01:50Z
> (`date -u`; catalog last built 2026-09-30T23:58:11Z) by Claude Code (Opus 5.5) in the planning worktree on
> `claude/next-phase-planning`. **Outputs:** `data/ticket_catalog.csv` (317 rows) and this note. **Read-only:** no
> control file, spec, ADR, manifest, LEDGER or production system was touched (P3, P10); nothing was committed. The
> generator and the checks live in the gitignored `docs/build/logs/next-phase/S1a/` (reproduction, §10).
> Evidence class for every catalog row: `inference` from the cited design notes (P1). Nothing here is a decision:
> S2 sequences, S1c carries the operator decisions, T3 writes contracts.

---

## 0. Bottom line

| class | rows | est. runs | what it is |
|---|---:|---:|---|
| **Stage-B seed** (`SEED-00…19`) | 20 | 23.2 | B3 C0–C10, B4 guard core, PKG-02 test rewrites, B1 correction records, B2 GATE DECISIONS restoration, T1/T3/T4/T5/T6 work |
| **Round-11 repo tickets** (`R11-*`) | 252 | 234.5 | of which **early R11** (wave 0 + memory/CI repair) 34 rows / 29.5 runs; **conditional** (I8 Wave D + keyed 511) 11 rows / 10.5 runs |
| **Operator actions** (`OP-01…23`) | 23 | 0 (operator hours) | skill releases, GitHub settings, merge sitting, DNS move, alias, domain, keys, reviews, confirmations |
| **Explicitly later** (`LATER-01…22`) | 22 | 25.0 | each with a named trigger (T-EVAL-IND, U-011 revisited, counsel, capacity, …) |
| **total** | **317** | | |

- **R11 est. runs by theme:** UX-CORE 56.5 · SOURCES 29.5 (10.5 conditional) · TRANSPARENCY 26.5 · DATA-CORRECTNESS
  23.5 · RELEASE-OPS 22.0 · R10-ACTIVATION 19.0 · SAFETY-HONESTY 18.0 · UX-EXPLORE 17.5 · MEMORY-TRUTH 10.0 · DEBT 5.5 ·
  GOVERNANCE-RECORDS 4.5 · CI-TOOLCHAIN 2.0 → **234.5** (224.0 without the conditional rows). 15 R11 rows are **L**
  (likely split at T3).
- **Merges:** 91 catalog rows fold outlines from ≥ 2 streams (21 of them are K13's earlier absorption of J3 TX-*);
  103 rows cite ≥ 2 ticket-shaped source keys. Every expected source id (22 families, 441 ids) is cited by some row
  (§4, coverage check green).
- **DAG:** 317 nodes, 749 edges, **acyclic** (Kahn); no seed row depends on an R11/later row; no R11 row depends on a
  later row. Longest seed→R11 chain 21.2 est. runs (§5).
- **Cost:** catalog delta **+$33.69/mo** (upper-bound point estimates) on the unverified ≈ $90–100/mo baseline →
  ≈ **$124–134/mo** vs the **$300** ceiling. No single item's expected cost exceeds $300. The only way past the ceiling
  is GCS-direct downloads/basemap if the DNS move (Q-31) is declined, or abuse egress before the budget alert and
  kill switch land (§6).
- **Gaps assigned by S1a:** 15 (§7). **Conflicts left for S2:** 17 (§8).

---

## 1. Method

1. **Read** META_PLAN §3, §7/§7.1 and the S1a row; then the ticket sections, dependencies and decisions of B1, B2, B3,
   B4, B6, E2, E4, F1 (+ `owed_register_adjudication.csv`), F2a, F2b, F3, F4, F5 (+ `eng_debt.csv` via F5 §4), G1,
   G2, G3, H1, H2, I8 (+ §8), J3, K13 (+ `k13_tickets.csv`, 118 rows), L1 §6, L3 §2/§9; D3 §4–5 and
   `review/REVIEW_SYNTHESIS.md` (S0 list RI-01…06) for scope checks; the K0–K12/J3 ticket tables only to fill scope
   lines for K13 rows whose K13 scope is a bare "= K4 JUR-01" reference.
2. **One owner per concern.** Where two streams outline the same work, one catalog row owns it and `merged_from`
   lists every source id; where one source item spans owners, it is **split** and each half is named (§3.2). No
   source item is dropped: a mechanical check (§4) requires every ticket-shaped id of every stream to appear in some
   `merged_from`.
3. **K13 is taken as already de-duplicated** across the K rows and J3: its 118 tickets become `R11-K13-<id>` rows
   unchanged in scope, size, wave and journeys; only their dependencies are mapped onto catalog ids (G2 ACT-*,
   F5 PKG-*, G3 REL-*, L3 CONF-*), and their soft dependencies ("soft", "interim … allowed", "optional", "if R2",
   "or the operator-named channel") move to `data_prereqs`.
4. **IDs.** Families that already carry stable keys keep them (`R11-ACT-NN` = G2 ACT-NN, `R11-REL-*` = G3,
   `R11-CONF-*` = L3, `R11-ACQ-*` = I8, `R11-K13-*` = K13, `R11-MEM-01…06` = B3 M1–M6). New or multi-source rows are
   numbered by theme (`R11-SAFE`, `-GOV`, `-OPS`, `-DATA`, `-DEBT`, `-SRC`, `-TRANS`, `-CI`, `-MEM-07…10`), plus
   `R11-ACT-17b` (PKG-03b's nginx half, companion to ACT-17). `class` is an added column (seed | r11 | operator | later).
5. **Sizes/runs.** S = 0.5, M = 1, L = 2 fresh-context runs everywhere (the J3/G3/K13 convention). This makes L3 15
   runs (L3 itself counted each unit as a run: 17), G3 11.5, I8 24.5, K13 102.5 (matches K13). Operator rows carry
   0 runs; their hours are in the scope text.
6. **Implicit dependency.** Every `r11` row depends on the seed having landed (`SEED-19`, GATE-B); this edge is not
   repeated in every row.
7. **Costs** are monthly deltas in USD against G1's list-price baseline, taken from each design's own cost lines
   (upper end where a range is given); one-off costs are in the scope/gate text, not in the column.

---

## 2. Where things land

| landing | seed | r11 | operator | later |
|---|---:|---:|---:|---:|
| stage-B seed | 20 (23.2 runs) | — | 5 (OP-01, 05, 07, 18, 23) | — |
| early R11 | — | 34 (29.5 runs) | 6 | — |
| R11 | — | 218 (205.0 runs) | 12 | — |
| later | — | — | — | 22 (25.0 runs) |

**Early R11 (first wave), 34 rows:** production safety and honesty — R11-ACT-01…08 (QA-1…10 via ACT-01/02/03/04,
publish path, honesty republish #1, attribution republish #2, API honesty code), R11-SAFE-01 (handles S0),
R11-SAFE-02 (forbidden-terms withdrawal), R11-CONF-02 (honest evaluation posture), the six K13 W0 copy tickets;
memory repair R11-MEM-01…10 and R11-ACT-12 (date truth in code); CI R11-CI-01 (TC-PIN, **deadline 2026-10-19**) and
R11-CI-02; R11-ACT-09 (sqitch hygiene, prerequisite for any hosted L44–52 deploy); R11-OPS-07 (calendar-bound
first-fire and 10-10 replay read-backs); R11-REL-10; R11-GOV-01.

**Stage-B seed, 20 rows:** SEED-00 (planning-ledger and credential-literal fixes, *before* GATE-P) · SEED-01 C0 ·
SEED-02 guard core (C0.5) · SEED-03 PKG-02 · SEED-04…07, 09, 10 = C1–C6 · SEED-08 B1 records outside
LEDGER/BUILD_INDEX + `p-17b713` supersession record · SEED-11 T1 ADRs · SEED-12 T1 spec_src · SEED-13 T3 · SEED-14 T4
registers · SEED-15 T4 validators · SEED-16 C7 · SEED-17 C8/T5 · SEED-18 C9 + seed PR · SEED-19 T6 + C10.

**Operator actions, 23 rows:** skill releases Tier A/B-must/B-should/C (OP-01…04; B6's 25 proposals); GitHub
S-2+S-3 before the seed push, S-1 after the merge sitting, S-4/S-5/S-7 (OP-05…07); the #141–#190 merge sitting and
tags (OP-08); DNS move to Cloudflare (OP-09, Q-31); `contact@` alias (OP-10); `sig-project.org` defensive
registration (OP-11); cost approvals and billing-admin steps (OP-12); HG-09 511 keys (OP-13); D-K2-1 organisation
review (OP-14); D-P32.3-1 dispositions (OP-15); D-P30.2b-1 curation (OP-16); OPCHECK per Class-S release (OP-17);
verbatim confirmations for records (OP-18); Zenodo production publish (OP-19); minisign key custody (OP-20);
search relevance set (OP-21); journey walkthroughs, gallery and copy batches (OP-22); optional branch backup (OP-23).
Decisions themselves (HG-03 lines, ING-GO-A…D, D-*, Q-*) are S1c's; the catalog names them in `operator_gate`.

**Later, 22 rows (trigger in each scope):** T-EVAL-IND human-evaluation segment (EV1 → H6 → EV-F → H8 → EV-D → EV-R,
H7) · live-site usability study · contribution-back · outreach/records requests/recruiting · counsel packet ·
contributor accounts · KYR content · Cloud SQL permanent scale/HA · acquisition long tail (Tier-2 remainder, Tier 3,
EDGAR, courts, paid data, tribal/territory channels) · QLD/NSW keyed APIs · OCR · deferred search/ZIP/K12b ideas ·
closeout-journal cutover · LEDGER rotation · G4c signing key · whole-graph canvas · OpenGov procurement · second
model family · cost-reduction options · legacy-bucket retirement · Ubuntu 26 runners · the public announcement.

---

## 3. Merge and split decisions

### 3.1 Merges (one owner per concern)

| concern | owner (cat_id) | absorbed | why this owner |
|---|---|---|---|
| Ops quick actions | R11-ACT-01/02/03/04 | G1 QA-1…QA-10, G1-02/03/04/05/10/14 quick halves, A1 NEW-2/3 | G2 already grouped QA by step 0a; G1 QA are the commands |
| Alerting beyond the quick actions | R11-OPS-02 | G1-02 ticket (a)–(e), G1-11 `sig-alerts`, F5 PKG-13 observability item, G1 NEW-3, J1 NEW-13 | one alert/probe owner; `observability.yml` truth is part of alert truth |
| Scheduler of record + cron lint | R11-OPS-03 | G1-09, G1-17, F5 PKG-13 cron lint (ED-58) + reingest retirement, I8 ACQ-01 cron lint, ADR-016/076/111(d) | three proposed cron-lint owners → one (CF-09) |
| Publish path | R11-ACT-05 | G1-06 ticket, F5 PKG-04 publish half, C4 NEW-10 no-delete | G3 assigns the allow-list and assertions to ACT-05 |
| Serving topology | R11-ACT-17 (+ ACT-17b) | F5 PKG-04 serving half, G3 §4.3, C4 NEW-9/14; PKG-03b nginx half → ACT-17b | G3's exactly-one ownership list |
| Release-archive + export-mode build | R11-ACT-16 | F5 PKG-03a, C4 archive NEWs, F5 NEW-5 | same files and ACs |
| Release-search states | R11-ACT-19 | F5 PKG-03b search half, C4 NEW-4/12/13/28 | same surface |
| Intake hardening | R11-ACT-20 | F5 PKG-05, C4 intake NEWs | identical scope |
| Sqitch hygiene | R11-ACT-09 | F5 PKG-01, D-P32.10a/16a-1, F1 2b, B1 §5.7 guard + comment lines, B4 B1-code sqitch part, Q-B1-1 | one ticket touching `sqitch.plan` |
| Attribution | R11-ACT-07 | F5 PKG-08, E2 H-2/E2-12, J1 NEW-2/3, J4 NEW-2/3/7, RI-03 | G2 step 0d; PKG-08 is its code |
| API honesty (S0 RI-02) | R11-ACT-08 | F5 PKG-09a, E2 H-5 (API), C3 NEW-1/10, J1 NEW-9 grants, J4 NEW-6 fixture sources | G2 step 0e |
| Identity base + crawler contact | R11-SAFE-06 | F5 PKG-09b, E2-08, E2 H-7 (UA), ACT-08 IRI part, F3 NEW-6, J1 NEW-8 | same identity-base setting |
| Date truth in code | R11-ACT-12 | B1 §5.4/§5.5/§5.8 code, B4 B1-code (G1 R2/R4 + literal test), F1 2e | G2 key kept; theme MEMORY-TRUTH |
| Honesty republish #1 | R11-ACT-06 | E2 H-1/H-3/H-4/H-6 (web), E2-02 gate move, A-1 text, C2 NEW-1, G1 NEW-7, C6 QW-2/3/4/5/15 | G2 step 0c |
| Officer-naming gate | R11-SAFE-03 | F2a group 1, E2 H-9 | same code path |
| Robots/opt-out/reservation | R11-GOV-04 | F2a group 4, E2-06, E2-07, E2 H-7 (policy text) | one collection-conduct owner |
| Toolchain + CI hygiene | R11-CI-01 | H2 TC-PIN, F5 PKG-13 items 1/6, H1 NEW-2/4 | H2 names TC-PIN first |
| CI truth verifier | R11-CI-02 | H2 TC-TRUTH, B4 CI-truth (G3b/G3c) | H2 already extended B4's ticket |
| Memory repair | R11-MEM-01…06 | B3 M1–M6 = B4 M1/M2/M3/M6 + G2 ACT-25 (→ M6) | B3/B4 agree |
| Test pins | SEED-03 + R11-MEM-08 | F5 PKG-02 rewrites + B4 G6 six-pin conversions → seed; PKG-02 lint + B4 pins-lint → MEM-08 | both designs require the pins before the seed; the lint can follow |
| Checker wiring | SEED-02 | F5 PKG-13 item 2, F3 BL-051/ADR-062, B4 G7 item 1, B4 NEW-4/9 | guard core already wires `docs-check` and CI |
| Verdict grammar/backlog checks | SEED-15 | F2b §2.4, B4 G7 items 2–4, F3 NEW-1/3, F5 PKG-13 item 3 | B4 places them with T4 |
| Jurisdiction key | R11-K13-JUR-01/02a | F5 PKG-06a (parts 1/2), F3 BL-053, ADR-079/122, F-44 | K13 already declared JUR-01/02a = PKG-06a |
| Point-in-polygon placement | R11-K13-JUR-02b | F5 PKG-06b point-in-polygon QA, L1 fix 6 geography | same function; residual detectors → R11-DATA-01 (CF-14) |
| Technology typing | R11-DATA-02 | F5 PKG-07, L3 CP-6, L1 fix 6 technology, L2 NEW-6, BL-044 part | L3 routes CP-6 to PKG-07 |
| Vocabulary + entity typing | R11-DATA-03 | F5 PKG-11, F2a group 13, L3 CP-3, L1 fixes 2 and 7, BL-047 | L3/K2 route typing to PKG-11 |
| Claim identity / keys / lineage | R11-CONF-03a/03b/04 | L1 fixes 1 and 3, PKG-06b IDOT/FL511, PKG-12 `derived_from` | L3's exactly-one list |
| Edge truth | R11-CONF-06 (backend) + R11-K13-GX-01/02 (labels, export) | L1 fix 5 | L3/K13 split already agreed |
| Dedup publication | R11-CONF-07a/07b (+ K13 QB-01 rendering) | L1 fix 4, K5 DSRC-04 | L3/K13 split already agreed |
| Honest eval posture | R11-CONF-02 | F4 EV2, L1 fix 8, E2-14 wording | L3 absorbs EV2 |
| Human-evaluation segment | LATER-01 | F4 EV1/H6/H7/EV-F/H8/EV-D/EV-R, rows 184–187, E2-14 reviewer path, E2-02 real review, E3 NEW-2 | U-008/U-011 → L3 option C |
| Lifecycle timeline | R11-DATA-05 | F2a group 5, PKG-12 lifecycle | same code |
| Ingestion hardening | R11-DEBT-03 | F2a group 10, PKG-12 disappearance + unwired scan | same framework |
| Run telemetry | R11-DEBT-04 | PKG-12 telemetry, J1 NEW-6 | J3 left it with PKG-12 |
| Projection rebuild + audits | R11-DEBT-01 | F2a groups 6+7, BL-048 | F2a allowed 7 into 6 |
| Security baseline | R11-OPS-08 | F2a groups 8 (minus SAs) and 9, G1-13, G1-14 ssl | F2a allowed 9 into 8 |
| Least-privilege SAs | R11-OPS-01 | G1-01, SEC-006 SA part, ACT-13 prerequisite | IAM change in one place |
| Execution host + DB logins | R11-ACT-13 | L3 CP-0 login, L2 NEW-16 | same infra pattern |
| Rights flips (owed rows) | R11-SRC-01 | F1 step 3 batch, E4 R3/R4a–d/R5/R6a/R6b | F1 asked for one batch ticket |
| D-R10-SOURCES-1 prep | R11-ACT-21 | F1 2d, E4 NEW-7/8, E4 B2 drafts, B6 rows, R6a terms capture | G2 = F1 |
| CCOPS breadth | R11-ACQ-14 | F3 BL-054, ADR-080(b) | I8 owns CCOPS acquisition |
| Archival deposits | R11-TRANS-01 (+ OP-19) | F1 D-P21.5-1, E2-21, BL-029, ADR-067/048 | one deposit owner; publish stays operator-run |
| J3 transparency tickets | R11-K13-TX-* | J3 TX-01…16 (TX-05a/b → K13 UX9-3/UX10-3a/b) | K13 C-09 |
| Release-model tickets | R11-REL-* | G1-07/F-08 cadence (→ REL-07), F-11/DR-C3-14 (→ REL-02), descriptor ADR (→ REL-01) | G3's exactly-one list |
| First model release | R11-ACT-24 | G2 ACT-24, G3 "first model release", F1 4e, K13 §7.4 JUR-03 ordering | G2 key kept |

### 3.2 Splits (one source item, two named owners)

| source item | halves |
|---|---|
| F5 PKG-13 | pins/cancel → R11-CI-01; checkers in CI → SEED-02; `check_backlog` → SEED-15; observability → R11-OPS-02; cron lint + reingest → R11-OPS-03; advisory → R11-CI-02 |
| F5 PKG-04 | publish → R11-ACT-05; serving → R11-ACT-17 |
| F5 PKG-03b | nginx tombstones/aliases/stubs → R11-ACT-17b; search states → R11-ACT-19 |
| F5 PKG-06b | point-in-polygon → R11-K13-JUR-02b; IDOT/FL511 → R11-CONF-03b; detectors, `axis_order`, 7 correction claims, portal rows → R11-DATA-01 |
| F5 PKG-12 | lifecycle → R11-DATA-05; disappearance + scan → R11-DEBT-03; telemetry → R11-DEBT-04; `derived_from` → R11-CONF-04; `/v1/changes` → R11-K13-TX-14 |
| E2 H-5 | API `/terms` → R11-ACT-08; governance doc → R11-GOV-01 |
| E2 H-6 | site footer/methodology → R11-ACT-06; manifest/LICENCES/datapackage → R11-ACT-07 (needs the re-export) |
| E2 H-7 | policy text → R11-GOV-04; UA/contact URL → R11-SAFE-06 |
| E2 H-8 | `sources.toml` "counsel" → R11-GOV-01; DEFERRALS corrections → SEED-14 |
| G1 QA-8 | `gh workflow disable` → R11-ACT-02; removing `schedule:` → R11-OPS-03 |
| B1 | LEDGER/BUILD_INDEX corrections → SEED-07; other memory/ADR/fixture records → SEED-08; JSONL → R11-MEM-03; code/fixtures → R11-ACT-12; sqitch comments/guard → R11-ACT-09; spec → SEED-12 |
| B2 restoration | GATE DECISIONS (step 1) → SEED-06; steps 2–7 → R11-MEM-04 (B3 placement; CF-07) |
| E4 lines | R3/R4/R5/R6 → R11-SRC-01; B1–B6 → R11-ACT-21/22; R1/R2/S1–S5 → SEED-14 records |
| F1 D-P32.3-1, D-P30.2b-1, D-P21.5-1 | engineering halves R11-DATA-08 / R11-CONF-11 / R11-TRANS-01; operator halves OP-15 / OP-16 / OP-19 |
| K5 DSRC-04 | export → R11-CONF-07b; rendering → R11-K13-QB-01 |

### 3.3 Dependency corrections applied while mapping

- **K13 W0 direction inverted.** `k13_tickets.csv` lists UXW0-1…6 as depending on G2 ACT-06/07 "(rides republish
  #1/#2)"; the content must exist before the republish, so R11-ACT-06 depends on UXW0-1/3/4/5/6 and R11-ACT-07 on
  UXW0-2 (CF-12).
- **Soft dependencies** (K13 "soft"/"interim allowed"/"optional"/"if R2"; G3 REL-06 → J3 TX-14 "first release is
  the baseline"; ACT-24 → research-dossier and intake routes; ACQ-28 → Wave D) are in `data_prereqs`, not
  `depends_on`. REL-06 → TX-14 as a hard edge would have made a cycle (TX-14 needs the release ACT-24 makes).
- **K13 §7.4 ordering constraint** "JUR-02b/03 before ACT-24" added as the edge R11-ACT-24 → R11-K13-JUR-03.
- **R11-CONF-01** lands in R11 wave 1, not wave 0: its spine probes need the `sig_audit` login from R11-ACT-13.

---

## 4. Completeness check (no silent drops)

`check_catalog.py` requires every id below to appear in some row's `merged_from` (regex, digit-bounded):

| family | ids | missing |
|---|---:|---|
| B3 C0–C10 · B3 M1–M6 · B4 G1–G11 | 11 · 6 · 11 | none |
| G1 QA-1…10 · G1 risks G1-01…17 (G1-16 closed by ADR-119) · G2 ACT-01…25 · G3 REL (13 units) | 10 · 16 · 25 · 13 | none |
| L3 CONF (16 units) · L3 CP-0…10 · L1 fixes 1–10 | 16 · 11 · 10 | none |
| F5 PKG-01…13 · F2a groups 1–14 · F1 owed rows | 13 · 14 · 36 | none (5 F1 rows are register-only dispositions in SEED-14/R11-OPS-07) |
| I8 ACQ-01…28 · E2 H-1…H-9 · E2 memos (21 + X1 + A-1) · E4 lines (22) | 28 · 9 · 23 · 22 | none |
| B6 SK-01…25 · H2 S-1…S-7 (S-6 is "no CODEOWNERS", no action) · H2 TC-PIN/TC-TRUTH · J3 TX-01…16 · K13 (118) | 25 · 6 · 2 · 16 · 118 | none |

Result: **441 expected ids, 0 missing; 0 schema errors; 0 ordering errors; 0 warnings** (`check_output.txt`).

---

## 5. Dependency DAG check

- **Result:** 317 nodes, 749 edges, every `depends_on` id exists, **no cycle** (Kahn's algorithm consumed all 317
  nodes; `cycle_nodes = []`). Seed rows depend only on seed/operator rows; R11 rows never depend on later rows.
- **Longest seed→R11 chain (est. runs 21.2, 21 rows):** SEED-00 → SEED-01 → SEED-03 → SEED-02 → SEED-04 → SEED-08 →
  R11-ACT-12 → R11-REL-01 → R11-K13-JUR-01 → R11-K13-JUR-02a → R11-DATA-04 → R11-REL-04b → R11-REL-06 → R11-ACT-24 →
  R11-K13-TX-13b → R11-K13-TX-14 → R11-K13-UX9-4 → R11-K13-UX10-3b → R11-K13-ACC-PLACES → R11-K13-CAP-01 →
  R11-K13-CAP-02. This is run count only; the real critical path is set by operator gos, the two monthly batch
  windows and **a second activated release** (TX-14), which is a calendar dependency (CF-13).
- Script: `docs/build/logs/next-phase/S1a/check_catalog.py` (exit 0).

---

## 6. Cost summary (monthly, USD)

| | $/mo | source |
|---|---:|---|
| baseline today (list-price inference, **unverified**; no billing export) | ≈ 90–100 | G1 §3.8 |
| catalog delta, seed + R11 + operator (upper ends) | **+33.69** | this CSV |
| → projected | **≈ 124–134** | vs **300** ceiling (U-008): ≈ $166–176 headroom |

Largest R11 items: R11-OPS-06 optional Cloud Armor +6 (Q-10) · R11-OPS-08 security scanning/audit logs +5 (log volume
unmeasured) · R11-REL-07 monthly cut writes + weekly materialize +4 · Wave B/C/D activations +2.5/+2.2/+1.5 · basemap
on R2 +2 · quality probe +2 · intake service +2 · alerts +1 · zero-egress host +1 · API/disk growth +1 · domain +1;
Artifact Registry cleanup −1. Without the optional Cloud Armor, the unmeasured audit-log/scanning estimate and Wave D, the delta is ≈ +$21/mo.

**Later (triggered, not in the projection):** Cloud SQL permanent tier +49 and optional HA ≈ +50 (LATER-08);
T-EVAL-IND evaluation database ≈ +10 (LATER-01); savings options −47 (LATER-19).

**Items that could push above $300 (none is a planned expense):**
1. **GCS fallback if Q-31 (DNS move) is declined:** downloads served GCS-direct $13–600/mo (abuse ≈ $2.8k; J3 §10) and
   the basemap on GCS $6–43/mo (K1) instead of ≈ $2–3 on R2. Stacking every later item on the GCS fallback lands at
   ≈ $300 before any real download traffic.
2. **Denial-of-wallet today:** world-readable buckets with no rate limit (≈ $120/day at 1 TB/day, G1 §3.8) until
   R11-ACT-01 (QA-7), R11-ACT-03 (budget alert) and TX-11's kill switch land.
3. **Operator-gated spend** (U-008: up to ≈ $1,000 only with a shown trade-off): none proposed. One-offs: drills
   ≈ $0.15–0.40 each, Wave-C tier bump ≈ $3, ≈ $2.4 of object writes per full release upload, counsel $0 (pro bono)
   to ≈ $3.5k–10.5k if ever pursued (LATER-05).

---

## 7. Gaps: work with no designed owner (S1a assigned one)

| # | gap | assigned |
|---|---|---|
| G-01 | D-J3-5 "withdraw forbidden-terms sources" is a first-wave must-ship (D3 §4) but no ticket executes it | R11-SAFE-02 (new) |
| G-02 | RI-01 personal-handle source ids: G2 put the rename in copy-only ACT-06, but a rename needs a re-export | R11-SAFE-01 (new; rides ACT-07) |
| G-03 | "visible spend ledger" (U-011, D3 §4) has no artifact | folded into R11-ACT-03 (monthly cost report) |
| G-04 | governance doc and `sources.toml` "counsel" corrections (H-5 doc half, H-8 repo half) | R11-GOV-01 (new) |
| G-05 | J4 NEW-6: OKC hand-seeded fixture sources served by the live API | R11-ACT-08 (API); `evidence.json` side rides K13 UXW0-2 — S2 confirm |
| G-06 | B1 correction records beyond LEDGER/BUILD_INDEX (B3 placed only C4) | SEED-08 |
| G-07 | F2a group 12 registry completeness / discovery sweep has no I8 home | R11-SRC-04 |
| G-08 | D-SOURCES.7-2 keyed 511 wiring absent from I8 | R11-SRC-03 (conditional) + OP-13 |
| G-09 | BL-025 parser canary, BL-026 WACZ (F3) | R11-SRC-06, R11-TRANS-02 |
| G-10 | read-only DB login (L2 NEW-16) named as "ops ticket" without one | R11-ACT-13 |
| G-11 | planning-ledger drift (B4 NEW-1/2) and the credential-shaped literal (H2 NEW-1) must be fixed before GATE-P/T6 by the planning orchestrator; no META_PLAN row owns them | SEED-00 |
| G-12 | operator-held artefacts: minisign key (D-J3-8), held-out relevance set (D-K3-7) | OP-20, OP-21 |
| G-13 | round tail: no single tail design; tail-like rows are CONF-14, ACQ-28, MEM-10, K13 TX-16/CAP-01/CAP-02, REL-11 | S2 defines the tail shape (META_PLAN S2) |
| G-14 | the 10-01…10-21 first-fire wave and 10-10 replay may run before Round 11 starts | R11-OPS-07 + the NEW-7 Track-0 question (S1c) |
| G-15 | the public announcement (U-009) is an operator act after CAP-02 | LATER-22 |

---

## 8. Conflicts left for S2

| id | conflict | catalog's provisional reading | decides |
|---|---|---|---|
| CF-01 | Guard core in the seed (B4 §6.1, ~700 LOC) vs "no code in the seed" (Q-14 fallback: row 201); also who owns "docs job on push" (SEED-02 vs H2 TC-PIN item 6) | in the seed (SEED-02) | Q-B4-1 / Q-14 |
| CF-02 | B1 §5.2 appends a date-correction footer to landed ADRs; B2/B4 `frozen-after-landing` allows only a Status-line change | footers in SEED-08, pending | S2: allow a `> Date correction` footer in the policy, or keep corrections only in the correction ADR |
| CF-03 | T4 (seed) writes DEFERRALS lead-token changes (F1/E4/L3/F2b), but the obligation-event tool is only repaired in R11-MEM-03 and `row-annotate` requires matching events | SEED-14 appends annotation text only; transitions follow MEM-03 | S2: this, or move MEM-03 into the seed |
| CF-04 | harness identity: B3's 19 fixed CURRENT STATE keys vs B5 OM-01 `harness:` (B4 NEW-10) | unresolved | Q-B4-4 / Q-B6-4 |
| CF-05 | G3's minimum set for the first model release omits REL-04b, but G3 makes REL-06 depend on REL-04b, which pulls JUR-02b, DATA-01, DATA-04 and ACT-07 into ACT-24's path | G3's stated edge kept | S2: REL-06 on REL-04a with V6–V10 advisory for the first release, or accept |
| CF-06 | D3 "US-nationwide; non-US not expanded" vs I8 Wave C (AU via OSM) and Wave D ACQ-23a/b (≤ 10 countries) | ACQ-23a/b conditional; QLD/NSW later | S2/S5 |
| CF-07 | B2 §6 puts all seven restoration steps in Stage B; B3 puts only C3 in the seed and the rest in M4 under M1 | B3 (SEED-06 + R11-MEM-04) | S2 |
| CF-08 | E2 recommends staffing reviews (E2-14 pilot, E2-02 external reader, Q-E2-15/01); U-008/U-011 and L3 supersede | LATER-01 | S1c must present Q-E2-01/15 consistent with Q-L3-2 |
| CF-09 | three cron-lint owners (G1-09, PKG-13, ACQ-01) | R11-OPS-03; ACQ-01 now waits on an ops ticket | S2 may move it to R11-CI-01 or ACQ-01 |
| CF-10 | API dossier fix: 404 (wave 0) vs the real jurisdiction scope (needs JUR-02a keys) | 404 in ACT-08; real scope soft | S1c/S2 |
| CF-11 | G1 wanted QA-1…5 before 10-01 and QA-9 before 10-09; §7.1 put them in Round 11 | early R11; NEW-7 exception open | operator (S1c) |
| CF-12 | K13's W0 rows list ACT-06/07 as prerequisites although they ride those republishes | inverted (§3.3) | S2 confirm |
| CF-13 | K13 TX-14/CHG-01/UX10-4/UX9-4 need "the second activated release", so CAP-01 (all journeys incl. J5) waits for a second release after ACT-24 | kept | S2: run CAP-01 with J5 pending, or schedule two releases |
| CF-14 | PKG-06b vs K13 JUR-02b: K13 lists "PKG-06b detectors" as JUR-02b's data prerequisite while both describe point-in-polygon | point-in-polygon → JUR-02b; detectors/corrections → R11-DATA-01 (hard prerequisite of CONF-07a/REL-04b) | S2 confirm |
| CF-15 | RI-01 is S0, but its rename rides the second republish (after ACT-07's attribution work), so it stays live longer than the copy fixes | R11-SAFE-01 before ACT-07's re-export | S2: ship a separate earlier re-export if the operator wants RI-01 first |
| CF-16 | Sizing conventions differ (L3 counts each unit as one run; J3/G3/K13 use S = ½) | S = 0.5 / M = 1 / L = 2 everywhere | S2/T3 sizing review |
| CF-17 | wave-0 bundling: ACT-07's re-export also carries SAFE-01, SAFE-02 and UXW0-2, so the S0 attribution fix waits on two extra operator decisions (D-J3-5, the handle confirmation) | bundled (fewer republish gos) | S2: unbundle if the decisions lag |

---

## 9. Columns (`data/ticket_catalog.csv`)

`cat_id, class, title, theme, scope, size, est_runs, depends_on, data_prereqs, operator_gate, live_stage,
monthly_cost_delta_usd, where_it_must_land, merged_from, source_refs, acceptance_sketch`. `class` was added (seed |
r11 | operator | later). `depends_on` is `;`-separated cat_ids (hard edges only). `live_stage` ∈ none · read-only ·
read-only + clone · production write (+ qualifier) · publish · production write + publish. `where_it_must_land`
begins with one of stage-B seed · early R11 · R11 · later, optionally followed by a parenthetical (deadline,
conditional, tail). `source_refs` paths are relative to this planning directory.

---

## 10. Reproduction (gitignored `docs/build/logs/next-phase/S1a/`)

```
python3 docs/build/logs/next-phase/S1a/build_catalog.py   # rows_a.py/rows_b.py/rows_c.py + data/k13_tickets.csv -> data/ticket_catalog.csv
python3 docs/build/logs/next-phase/S1a/check_catalog.py   # schema, ordering, DAG, coverage, totals, cost (exit 0) -> check_output.txt
python3 docs/build/logs/next-phase/S1a/merge_stats.py     # merge counts
```
