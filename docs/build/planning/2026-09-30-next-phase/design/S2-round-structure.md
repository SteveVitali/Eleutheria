# S2 — Round 11: structure, priorities, sequencing and success criteria

> **Row:** S2 (META_PLAN §6.S), S/J, depends on S1a, S1b, S1c and D3. **Authored:** 2026-10-01T00:34:47Z – 01:05:48Z
> (`date -u` at start and at the final check) by Claude Code (Opus 5.5) in the planning worktree
> `/Users/stevenvitali/Eleutheria-next-phase`, branch `claude/next-phase-planning`, HEAD `0a8a6296`.
> **Outputs:** this note and `data/round11_plan.csv` (333 rows: 262 chain rows 201–462, the 4 superseded rows 184–187 as
> markers, and every seed, operator and later unit of the S1a catalog, so one file accounts for all 317 catalog units).
> **Read-only:** no control file, spec, ADR, manifest, LEDGER or production system was touched (P3, P10); nothing was
> committed; no production read was made by this row. **Evidence class:** `inference` from the cited design notes,
> except dates (`date -u`) and the mechanical checks in §12. **Nothing here is a decision.** Every operator choice is an
> S1c line; this note only says which row waits on it and what its default does to the plan. Agent-drafted text meant
> for the LEDGER (§3.5) is labelled as such.

---

## 0. Bottom line

**Round 11 runs as one round with four gated sub-rounds and one right-sized tail.** It is about 6× Round 10 (40 rows,
161–200). Each sub-round is about Round-10 size, ends in a 0.5-run live-read acceptance row and an operator check-in
GATE, and carries one purpose that follows D3's order: safe and honest → correct → explorable → explored and proven.

| sub-round | phase | rows | est. runs | purpose | ends with | expected window (inference, §5.4) |
|---|---|---|---:|---|---|---|
| Stage-B seed | — | 20 units (not chain rows) | 23.2 | memory truth, guard core, ADRs, spec, manifest, registers | **GATE-B** (+ 11A pre-authorisation) | 10-03 → 10-06 |
| **11A — Safe, honest, truthful** | P34 | 48 (201–248) | 44.0 | every S0 closed live; production protected; CI pinned and read; memory guards; date truth; Round-10 schema live; quality baseline | P34.47 acceptance + **GATE-G4** | R0 ≈ 10-06 → ≈ 10-16 |
| **11B — Correct and traceable** | P35 | 65 (249–313) | 62.5 | Stream-L identity core + F5 data fixes + placement; transparency exports and labels; release pipeline; Wave A; **first model release** with the dedup | P35.63 (HG-11) + P35.64 + **GATE-G5** | ≈ 10-16 → ≈ 10-29 |
| **11C — Explorable core** | P36 | 74 (314–387) | 65.0 | Wave B + the second release; design system; every U-003 ask gets a working page; core-surfaces release | P36.72 (HG-11) + P36.73 + **GATE-G6** | ≈ 10-28 → ≈ 11-16 |
| **11D — Explored and proven** | P37 | 68 (388–455) | 62.0 | Wave C (+ conditional D); graphs, explorer, watch feeds, raw archive, disagreements, changes; `/quality/`; stream acceptances; final release; journeys | P37.65 (HG-11) + P37.68 CAP-01 | ≈ 11-16 → ≈ 12-05 |
| **Round tail** | P38 | 7 (456–462) | 5.0 | CAP-lite (2 rows) → **GATE-ACCEPT-R11** → REC (1) → DOC (1) → announce-readiness → **GATE-ANNOUNCE** | — | ≈ 12-05 → ≈ 12-10 |
| **total** | P34–P38 | **262** chain rows | **238.5** (229.0 without the 9.5 conditional runs) | | 5 gate markers, 11 in-ticket pauses | |

- **Conflicts:** all 17 of S1a's conflicts are resolved (§2.1). The ones that shape the plan: the guard core stays in the seed (CF-01);
  date corrections never touch landed ADRs (CF-02); the seed queues DEFERRALS lead-token transitions for MEM-03 (CF-03);
  the first model release runs the full V1–V15 suite (CF-05); Round 11 stays US-first and ACQ-23a/b leave the round
  (CF-06); and J5 runs on a real multi-release diff (CF-13).
- **S1b assumptions:**
  - "First waves" = 11A ∪ 11B. All 76 S0/S1 owner units and their prerequisites (78 runs) are placed there; this was
    checked mechanically.
  - All 9 S0 owners are in 11A.
  - The 8 L1/L2 correctness S1s are **pulled forward into 11B** (L3 had them in waves 2–3), together with the OPCHECK protocol.
- **nextTicket at seed:** row 201 = **P34.1 TC-PIN** (R11-CI-01), which has the 2026-10-19 deadline.
- **Calendar critical path.** No Round-10 schema before 10-14 → step 1 at P34.46 → Wave A (10-19→23) → first model release
  P35.63 → Wave B (10-26→11-05) → no cut during 11-06→13 → core-surfaces release → Wave C (11-16→20) → final release outside
  12-06→13 → journeys → GATE-ACCEPT-R11 → GATE-ANNOUNCE. Engineering runs ahead of these windows. The windowed live legs wait in a
  **live-leg queue**, a stricter RETURN PASS (§3.5, OM-19).
- **Budget (S1a upper ends on G1's unverified ≈ $90–100/mo baseline):**
  - after 11A ≈ $95–105; after 11B ≈ $96–106; after 11C ≈ $111–121; after 11D ≈ $123–133 (+ ≈ $1 domain);
  - without the DNS move, ≈ $127–174;
  - **nothing needs an over-$300 approval** (§9);
  - agent spend is reported per sub-round, separately from the infra ceiling (A-2).
- **Top findings for S3/S5:**
  - **B-24's default stalls the critical path.** If B-24 (HG-03 for the public-domain boundary sources) is unanswered,
    JUR-01 cannot capture boundaries, so the jurisdiction S1 fixes and the first model release wait. Move B-24 into Part A.
  - **Nine more defaults quietly descope operator asks** (§7.3). The success criteria in §8 are stated conditionally on
    those answers.

---

## 1. Inputs, method and checks

**Read:**
- META_PLAN §1, §3, §6.S, §7, §7.1 and the §11 change log from S1a onward;
- `feedback/OPERATOR_FEEDBACK.md` (U-001…U-015);
- **S1a**: `data/ticket_catalog.csv` (317 rows) and `research/S1a-ticket-catalog.md`;
- **S1b**: `universe/DISPOSITIONS.md`, `universe/UNIVERSE_DISPOSED.csv` and `tools/check_dispositions.py` (`first_waves()`);
- **S1c**: `design/S1c-decision-catalog.md` §0–§8 and `data/decision_catalog.csv`, for the defaults;
- design notes, in the sections listed:

| note | sections |
|---|---|
| D3 | all |
| K13 | §0, §7, §8, §9, §11 |
| G2 | §0–§3 |
| G3 | §7 and §11–§12 |
| I8 | §0, §7.1–§7.3 and §8–§11 |
| L3 | §0, §3.3, §6 and §9–§11 |
| B3 | §1, §3.4, §3.12 and §5 |
| B4 | §0, §6 and §9 |
| H2 | §0, §3.5 and §9 |
| B5 | §0, §3.13, §4.2 and §6 |
| B6 | §0, SK-20 and §5 |
| G1 | §3.8 (cost) |

- `baseline/TRACK0_RECORD.md` (Track 0.5 alerting, executed 2026-10-01T00:09Z);
- the manifest's Round-10 rows 161–200;
- the two skills `orchestrate-build` and `decompose-spec` (`SKILL.md`: sizing, markers, gates, tail).

**Method.**
1. **Fix the constraints.** These come from:
   - the S1a DAG (749 hard edges);
   - S1b rule (c), which binds the S0/S1 owners;
   - the fixed calendar (G1, G2, G3, I8, H2);
   - the operator's constraints (§7.1, U-008, U-011, U-012).
2. **Group by purpose.** Units are grouped into four sub-rounds that follow D3's order (safety/honesty → correctness →
   exploration, with Streams I and L in parallel).
3. **Order within each sub-round.** The rules in §5.5 apply, and every hard edge must point backwards.
4. **Add 24 S2 sequence edges on 14 rows.** These are marked `(S2)` in `depends_on`, each with its reason in `notes`.
5. **Add the S2 rows.** These are new rows and markers: three acceptance rows, five gate markers, CAP-lite (two rows), REC
   and DOC, the four 184–187 markers, and non-chain rows for every seed, operator and later unit.
6. **Annotate every gated row.** Each gets its S1c decision id, packet line and default. Production-touching rows also get
   their window.

**Checks** (scratch builder outside the repo, re-runnable from the CSV; §12):
- every S1a unit appears exactly once (LATER-01 also names the four markers);
- 0 order violations over the catalog edges and the S2 edges;
- the S0/S1 owner closure is entirely in 11A ∪ 11B;
- the run totals by sub-round match §0.

---

## 2. Decisions this row makes (S2's own scope)

### 2.1 S1a's 17 conflicts

| id | decision | rationale | lands in |
|---|---|---|---|
| **CF-01** | **Keep the guard core in the seed** (SEED-02), as A-13 recommends. **R11-CI-01 owns the `docs` job's `push` trigger**, `cancel-in-progress` for PRs only, and the pinned-test rewrite with its ADR. SEED-02 only wires the guards into the existing PR-triggered `docs` job and `make docs-check`. **A-13 fallback:** if A-13 defaults to a records-only seed, T3 inserts SEED-02/03 as P34.0a/P34.0b at rows 201–202 and renumbers by +2. Nothing has landed, so renumbering is free | The seed writes exactly the record classes where F-21/F-22/F-29 happened. GATE-B needs CI green, which needs the six pin conversions (B4 §6.1, NEW-3). A push trigger only matters on `main`, which agents never push | SEED-02; P34.1 |
| **CF-02** | **Landed ADR bodies stay frozen; no date footers.** Date corrections live only in the single correction ADR (from ADR-146) and `reports/memory-repair/date_corrections.csv`. The ADR-index generator (P34.32) derives a "date corrected → ADR-nnn" marker from that register | One owner. Zero exceptions to the frozen-after-landing policy, so no per-ADR guard allowances. It honours AGENTS.md ("a decision change is a new ADR"), and the index keeps the correction visible | SEED-08, SEED-11; P34.32 |
| **CF-03** | **SEED-14 appends annotation text only.** Every DEFERRALS lead-token transition the seed would make (E4 S1/S2/S4, F1 D-P21.3-2, …) is queued in a `pending_transitions` list under `reports/memory-repair/`. **P34.8 MEM-03 applies the whole queue** through the repaired tool. SEED-15's cross-check treats queued rows as expected. The 11A exit requires 0 pending | Keeps the seed minimal (Q-14). The guard forbids token changes without events. Leaving OPEN rows unchanged for a few days is the conservative state; the decisions themselves are in GATE DECISIONS from GATE-P | SEED-14/15; P34.8 |
| **CF-04** | CURRENT STATE gains **an optional 20th key, `harness:`** (≤ 256 B; e.g. `claude-code / claude-opus-5-5 / subagent`), validated by G5 V12. It also goes in the run-ledger header and the PHASE LOG field (B6 Q-B6-4) | OM-01 needs a value an orient can read. `dispatchTarget` means something else, and B4 already reserves V12 for it | SEED-17; P34.9 |
| **CF-05** | **Keep G3's edge: REL-06 → REL-04b.** The first model release (P35.63) runs the full V1–V15 suite with no advisory checks | 11B already orders every correctness row before P35.63, so the edge costs no calendar time. The first release is the immutable baseline that every later diff and citation (TX-14, J4) is measured against | P35.58–P35.63 |
| **CF-06** | **US-first holds** (D3, A-17; B-34 default). **R11-ACQ-23a/b leave Round 11 for LATER-09**, triggered when the operator revisits D3's US-first scope *and* answers the B-34 N-lines "a". **Wave C's OSM-origin query is scoped to the US and territories**, the layer it replaces. Non-US per-country object counts are logged, not ingested. Wave D keeps only US and territory families. T3 drops ACQ-23a/b from ACQ-27's `depends_on` | D3 says "non-US dossiers are corrected but not expanded". No counsel reviews the database right (B-34), and Wave D is droppable as a whole (I8). The operator can reverse this at S5 through A-17 | P37.2, P37.54; LATER-09 |
| **CF-07** | **B3's placement:** C3 (GATE DECISIONS restoration, restore first) in the seed; B2 steps 2–7 in **P34.27 MEM-04**, run under M1's full append-only modes | The six rows that exist nowhere else are restored before the head is touched (A-13). The other steps need M1 to prove each one *is* a restoration, plus the operator's addenda confirmations (OP-18) | SEED-06; P34.27 |
| **CF-08** | **No Round-11 staffing rows.** E2-14 and E2-02 human review and Q-E2-01/15 are presented as consistent with Q-L3-2 (A-6). The ACT-06 republish ships `/editorial-standards/` reading "not yet performed". UI-042 and DOS-002 stay owed under T-EVAL-IND | U-008 and U-011 leave no reviewers and allow no outside contact; L3 option C | P34.17; LATER-01 |
| **CF-09** | **R11-OPS-03 is the sole owner of the cron lint** and the scheduler of record. It sits first in 11B, before ACQ-01 | Fleet-wide scheduler policy is ops, not acquisition, and CI-01 must stay lean for its 10-19 deadline | P35.1 → P35.6 |
| **CF-10** | **Two steps:** ACT-08 ships the honest "scope not available" 404, live through P34.46 (Round-10 API). **REL-05 (P35.57) owns the real jurisdiction-scoped dossier API** after JUR-02a (P35.18). No API hotfix unless P34.46 slips past 10-21 (B-7) | An honest refusal now; real scope once keys exist. That avoids a hotfix outside the release model | P34.25, P34.46, P35.57 |
| **CF-11** | **Mostly overtaken by events.** Track 0.5 (2026-10-01T00:09Z) already created the alert channel, 2 uptime checks and 4 alert policies. **P34.4 ACT-02 verifies, extends (QA-5 `sig-probe` re-roll, QA-8 disable) and codifies them**; P35.2 makes them code. QA-9 (the restore drill) stays at **P34.6**, early in 11A. A-1 now governs only whether the drill runs before 10-10 as a Track-0 exception | Production fixes are Round-11 tickets (§7.1). Only the operator can grant a Track-0 exception | P34.4, P34.6, P35.2 |
| **CF-12** | **Confirm the inversion.** Content rows precede the republish that ships them: P34.11–15 → P34.17 (ACT-06), and P34.18–20 → P34.21 (ACT-07) | "Disclosure before exposure" (AR-6); one publish per go | P34.11–P34.21 |
| **CF-13** | **Several real releases before CAP-01.** P35.63 is the first model release. P36.12's Wave-B release is the **second activated release** (REL-11 accepts it at P36.70). P36.72 and P37.65 follow. TX-13b and TX-14 (P36.66–67) are built in 11C after P35.63. J5 then runs on a real diff of at least two releases, not "pending" | D3 makes J5 a capstone journey. Cadence requires release-to-release diffs anyway (G3) | P35.63, P36.12, P36.66–70, P37.68 |
| **CF-14** | **Confirm the split.** Point-in-polygon goes to JUR-02b (P35.19). Detectors, `axis_order`, correction claims and portal rows go to **DATA-01 (P35.16)**, which is a hard prerequisite of CONF-07a and REL-04b. **New S2 edge: JUR-02b after DATA-01**, so placement runs on corrected axis order (562 swaps) | One owner per concern, and placement over swapped coordinates would be wrong | P35.16 → P35.19 |
| **CF-15** | **Keep RI-01 riding the ACT-07 re-export**, with SAFE-01 ordered directly before it (P34.18 → P34.21). The re-export happens at the first slot after the AR-3 window ends (2026-10-13T12:00Z); about 5–7 days after republish #1 if R0 ≈ 10-06. **Operator override:** at S5, B-3 can ask for "RI-01 first". T3 would then add an export-only republish with no hosted write, which is allowed during AR-3 outside 03:00–10:00Z | One hosted backfill and one republish go instead of two. The handles have been public since at least 09-27; a week's difference against an extra operator stop is the operator's call | P34.18, P34.21 |
| **CF-16** | Estimates use **S = 0.5 / M = 1 / L = 2** everywhere. **T3 splits all 15 L rows into a/b** (P34.21, .22, .24, .34, .42; P35.1, .14, .15, .20; P36.1; P37.4, .5, .16, .46, .57), giving ≈ 277 rows. T3 also checks adjacent S rows that touch the same files for a merge (over-factoring) | decompose-spec rule 1 (one fresh subagent context, a hard ceiling); CF-16's mixed conventions | T3 |
| **CF-17** | **Keep the bundle** (SAFE-01, SAFE-02 and UXW0-2 in ACT-07's re-export), because **both decisions have actionable defaults**. A-8 defaults to withdraw-and-restrict; B-3 defaults to re-key. No unanswered line can hold back the S0 attribution fix | Fewer republish gos (B5 approval fatigue) with no stall risk | P34.18–P34.21 |

### 2.2 S1b's provisional assumptions

1. **"First waves" = 11A ∪ 11B.**
   - **S0 owners.** All 9 S0 findings land in 11A, and all are live-closed by P34.46 at the latest (F-130 closes when the
     Round-10 API rolls).
   - **S1 findings.** Of the 104:
     - 99 land on a seed unit (11), an 11A row (50) or an 11B row (38);
     - 1 lands on OP-11 (F-184), due by GATE-G4;
     - 1 is already done (F-366);
     - 3 are decisions answered at S5:
       - F-31 → A-4;
       - F-191 → C-3;
       - F-386 → A-3, with TX-11 (P35.5) placed early in 11B against the denial-of-wallet risk.
   - **The binding set.** It is the transitive closure of the S0/S1 owners plus the interim units: **76 units, 78 runs**.
     All of it is in 11A ∪ 11B. This is checked (§12).
   - **S2 narrows S1b's provisional set.** S1b's `first_waves()` holds 102 R11 units. 83 of them are in 11A/11B. **19
     non-owner K13 W1 units (17 runs) move to 11C next to their consumers.** They are:
     - the design system (UXK14-1/2/3a/3b/4/5);
     - the IA kit (UXK0-3/4/5);
     - the figure kit (FIG-01a/b);
     - GX-03/04;
     - SRCH-01/02 and MAP-02;
     - RQ-01;
     - UX10-1/2.

     No S0/S1 item lands on any of them, so rule (c) still holds. **S3/T4 should switch rule (c) to read
     `sub_round ∈ {11A, 11B}` from `data/round11_plan.csv`** instead of the provisional catalog-derived set.
2. **The 8 L1/L2 correctness S1s are pulled earlier, into 11B.** They were planned for L3 waves 2–3.

   | row | fix | findings |
   |---|---|---|
   | P35.24 | CONF-03b | F-506, F-518 |
   | P35.25 | CONF-04 | F-507 |
   | P35.26 | CONF-06 | F-521 |
   | P35.27 | CONF-05 | F-519 |
   | P35.46 | CONF-07a | F-520 |
   | P35.47 | CONF-07b | F-511 |
   | P35.61 | ACT-14 | F-522 |

   CONF-10 and CONF-11 (P35.48–49) come forward with them. The interim mitigations stay in 11A: CONF-01 (P34.44, the
   ratchet) and UXW0-2 (P34.20).

   **Why:**
   - D3 says correctness comes before exploration, "so that new maps and graphs do not amplify known errors". K13 R-1
     (the UX ships ahead of the data) is the same risk seen from the UX side.
   - B-26 makes the dedup an announce criterion.
   - The first model release is the immutable baseline. Shipping it with 5,278 collided subjects and publisher-as-operator
     edges would freeze them into citable URLs.
   - Putting the OPCHECK protocol before P35.63 lets the operator's own blind-first check accompany that release. It
     answers U-006 ("I haven't done a deep audit of the mechanism").
   - **Cost:** 11B grows by about 9 runs; 11D shrinks by the same.

---

## 3. Round structure

### 3.1 Shape

```
GATE-P ─ Stage-B seed (23.2 runs) ─ GATE-B [pre-authorises 11A named mutations]
  └─ 11A P34 (44.0) ─ P34.47 acceptance ─ GATE-G4 [budget · publication · rights · pre-authorise 11B]
      └─ 11B P35 (62.5) ─ P35.63 first model release (HG-11) ─ P35.64 ─ GATE-G5 [+ ING-GO-B, D-K2-1 review]
          └─ 11C P36 (65.0) ─ P36.12 Wave-B release (HG-11) ─ P36.72 core-surfaces release (HG-11) ─ P36.73 ─ GATE-G6 [+ ING-GO-C/D, Q-23]
              └─ 11D P37 (62.0) ─ P37.65 final release (HG-11) ─ P37.66–68 stream acceptances + journeys
                  └─ tail P38 (5.0): CAP.1 ─ CAP.3 ─ GATE-ACCEPT-R11 ─ REC ─ DOC ─ CAP-02 ─ GATE-ANNOUNCE
live-leg queue (OM-19): windowed live legs run at ticket boundaries once `date -u` is inside their window and their go is recorded
```

### 3.2 Why gated sub-rounds (B5's lessons)

| B5 lesson | how this structure answers it |
|---|---|
| **The tail cost a lot and read nothing live** (P33.4–P33.8: 5 PRs and 3,047 lines; 0 production or CI reads; it re-certified stale text; NEW-5) | **Per sub-round:** one 0.5-run acceptance row. It reads CI for every PR, the production probes, the backups, the scheduler, the quality suite and the billing export, and drafts the check-in packet.<br>**Per round:** CAP-lite (CAP.1 M + CAP.3 S) + GATE-ACCEPT-R11 + **one** REC + **one** DOC. That is 4.5 runs, against Round 10's 9-row tail. Every tail row carries SK-20's `(live-read)` acceptance criterion, and stream acceptances (TX-16, ACQ-28, CONF-14, CAP-01) are ordinary 11D rows that do real measurement |
| **Gates became a throughput device** (35/76 answered at a pause; `blockedOn` never used; readouts written after the approvals) | Five gate markers and eleven in-ticket pauses, each tied to a real decision:<br>• money over the ceiling;<br>• a Class S exposure, one candidate-specific readout each;<br>• a rights flip;<br>• a per-wave ingestion go;<br>• two risky spine writes (P34.46, P35.61).<br>Each check-in sits **after** an acceptance row, so the evidence is on screen. Silence pauses the chain and is never consent (OM-18). Publication is **never** pre-authorised |
| **Autonomy outran verification at the repo boundary** (16 red PRs; CI never read) | Row 201 is TC-PIN and row 202 is TC-TRUTH (flake policy and the recorded-CI verifier), so every later boundary reads head-bound CI through the seed's G3a. An acceptance row cannot pass with an unexplained red |
| **Status words collapsed layers** ("34 MET" vs "fixtures only") | Each acceptance row reports the **highest layer reached per row** (engineered / fixture / staging / live / public / human). Exit criteria (§8) are written at the live or public layer |
| **Planning outside a reviewed plan; mid-round harness switches** | Every row comes from this reviewed plan. At each check-in, `decompose-spec mode=extend` re-checks the sizing of the next phase (append-only Plan extensions; OM-03). One harness for the whole round (A-15, OM-01) |
| **Size** | Each sub-round is ≤ 65 runs and ≤ 74 rows: 1.2–1.9× Round 10's 40 rows, against 6.6× for a flat round. **Re-split rule:** if a phase exceeds 75 runs or 85 rows after T3's splits, it becomes two phases with an extra GATE |

### 3.3 Why this follows the existing patterns (U-012: "previous builds worked pretty well … follow the existing patterns")

It is still **one round, one manifest, one LEDGER and one `orchestrate-build` loop**:
- phases and rows continue (P34+, rows 201+);
- one ticket per fresh `implement-spec` context and one stacked PR per ticket, on the chain tip `devin/p33-8-agent-docs-refresh`
  (#190, `b051732c`), never merged by agents;
- `GATE-G<k>` markers, the same device Round 10 used mid-round (GATE-G3, row 190);
- `RETURN PASS`, `decompose-spec mode=extend` and the decompose-spec tail templates, right-sized as SK-20/SK-22 propose.

Only **two operating clauses** are added, and both make an existing mechanism stricter rather than adding machinery:
- **OM-19** turns RETURN PASS into a dated live-leg queue;
- **OM-20** applies OM-10's own rule to a bounded per-sub-round pre-authorisation.

### 3.4 Alternatives considered

| alternative | why not |
|---|---|
| One flat round, full tail at the end | 262 rows with no evidence-bearing stop between GATE-B and GATE-ACCEPT. That is Round 10's failure mode at 6× scale; the operator would first see layered status after about 9 weeks |
| Four separate rounds (11–14), each with its own decompose, GATE-P and tail | 4× tail cost (B5 NEW-5) and four ratification sittings. The S0/S1 first-wave constraint spans 11A and 11B anyway. It also contradicts U-012 and U-011 (more ceremony, less autonomy) |
| Five sub-rounds of about 48 runs | One more pause, with no extra decision content. It is held in reserve by the re-split rule (§3.2) |
| Calendar-driven sub-rounds (one per batch window) | The chain would idle for weeks while engineering waits on windows. The live-leg queue decouples the two instead |

### 3.5 Operating additions for T5 (agent-drafted; ratified at S5, written by T5)

> **OM-19 WINDOWS AND THE LIVE-LEG QUEUE.**
> - **Recording a leg.** A contract whose live stage has a window or a named go carries a `Live window:` header. When it is
>   dispatched, the ticket lands its engineering and its staging state. If `date -u` is outside the window, or the go is
>   missing, the live leg goes into RETURN PASS with its window, its go id and its re-run line, and the chain continues.
> - **Running legs.** At every ticket boundary, the orchestrator compares `date -u` with the live scheduler state and the
>   queue (never the latest recorded date; AR-4). It re-runs the owning ticket in live mode for each leg that is now due,
>   before dispatching the next row.
> - **Dependent rows.** A row whose `depends_on` names a queued leg's **live result** (T3 marks those edges `live:`) waits.
>   That wait is a pause, not a block.
> - **Gates.** No sub-round GATE packet is presented while a leg whose window has opened is still unexecuted. Each
>   execution is recorded with its pre-state, restore point, rollback command and probe result (OM-14, AR-2, AR-5).

> **OM-20 PRE-AUTHORISATION (bounded; OM-10).**
> - **What it covers.** At GATE-B, and at each sub-round GATE, the operator may pre-authorise the **named production
>   mutations of the next sub-round**. The list gives exact row ids, the mutation each contract names, its restore point,
>   and an expiry at the next GATE.
> - **Never pre-authorised:**
>   - HG-11 / Class S promotions and republishes;
>   - ING-GO;
>   - HG-03 flips;
>   - the spine schema change (P34.46);
>   - the bounded apply (P35.61);
>   - the Wave-C tier bump;
>   - any spend above $300/mo.
> - **Voiding.** A new material fact voids the pre-authorisation for the affected rows: a red probe, a failed restore point,
>   or a production read that contradicts a record.
> - **When nothing is pre-authorised.** Each named mutation becomes an in-ticket pause. That is about 84 live rows (§7.1).

**Sub-round acceptance row (P34.47, P35.64, P36.73; S; read-only).** It reads and records the following as a
`probe-run/1` record plus an acceptance note:
1. G3a head-bound check-runs for every PR of the sub-round, with flake re-runs;
2. production probes:
   - `sig-ops probe-hosted` and the G10 probes (from P35.3);
   - backups and PITR;
   - the scheduler live-diff;
   - present/absent route probes;
3. the quality suite: ratchet regressions = 0, and the checks flipped to `enforce`;
4. the layer reached by each row;
5. the live-leg queue state;
6. new deferrals and obligation events;
7. a spend line: the billing export month-to-date and forecast, plus agent runs and usage (§9.5);
8. merges the operator made, read from GitHub.

It then drafts the GATE packet (§3.6). It writes no production state.

### 3.6 The check-in GATE (G4, G5, G6), scoped to budget, publication and rights

The packet is agent-drafted and labelled. It has five parts:
1. **Budget:**
   - infra month-to-date, forecast and projection for the next sub-round against $300;
   - agent runs and usage;
   - any line that would exceed the ceiling, which is an approval line (none is expected).
2. **Publication:**
   - the Class S promotions this sub-round, linking their signed readouts;
   - those planned for the next sub-round, with dates and new route families.
3. **Rights:**
   - the HG-03 lines the next sub-round needs, each with its default;
   - the ING-GOs whose windows fall in it, verbatim.
4. **The OM-20 pre-authorisation list** for the next sub-round.
5. **Status, for information only:**
   - layered status;
   - the queue;
   - CI incidents;
   - anomalies;
   - operator-side merges.

**Answers:**
- `continue`, which is a complete answer: every line inside takes its own default;
- `continue with <lines>`;
- `pause`.

The answer is recorded verbatim in GATE DECISIONS and `readouts/GATE-G<k>.md`, and never proxy-signed (OM-07/08).

---

## 4. The sub-rounds

Row ids are in the CSV; theme run totals come from S1a's `theme` column.

### 4.1 11A — Safe, honest, truthful (P34, rows 201–248, 44.0 runs)

**Contents.**
- **CI first:** P34.1 TC-PIN and P34.2 TC-TRUTH.
- **Production safety:** P34.3–P34.6 (QA-1…QA-10, budget alert and billing export, restore drill).
- **Memory guards:** P34.7–P34.9 (M1, M3, M2) and P34.27–P34.33 (M4–M10).
- **Honesty:**
  - the one allow-listed publish path (P34.10);
  - six W0 copy rows (P34.11–15, P34.20);
  - repo honesty (P34.16);
  - **republish #1** (P34.17);
  - handle re-key and forbidden-terms withdrawal (P34.18–19);
  - **attribution re-export and republish #2** (P34.21).
- **Truth in code:** date truth (P34.22) and versioning (P34.23).
- **Activation prerequisites:**
  - sqitch hygiene and the L44–52 clone rehearsal (P34.24);
  - API honesty (P34.25);
  - ADR-124 allow tooling (P34.26);
  - C4 blockers (P34.34–P34.38);
  - serving topology, dark (P34.40–41);
  - least-privilege identities, execution host and `sig_audit` login (P34.42–43);
  - **quality baseline in ratchet mode** (P34.44);
  - honest evaluation posture (P34.45);
  - **G2 step 1: Round-10 schema, allows and API** (P34.46), after the 10-10 read-back (P34.39).

**By theme (runs):**

| theme | runs |
|---|---:|
| safety and honesty | 14.0 |
| Round-10 activation | 13.0 |
| memory truth | 10.0 |
| release ops | 3.0 |
| CI | 2.0 |
| data | 1.0 |
| governance | 0.5 |

**Entry.**
- GATE-P has ratified the plan. Part A is answered, or its defaults are recorded *as defaults*.
- SEED-00…19 have landed.
- **GATE-B** is recorded verbatim, with the 11A OM-20 list: P34.3–6, P34.21 (backfill leg), P34.24, P34.40, P34.42–45.
- The seed PR is 5/5 green (P11).
- The orient dry-run resolves `nextTicket = 201`.
- OP-02 (skills Tier B-must) is applied, or T5's B6 §5.3 overrides are in force.

**Exit** (P34.47 checks each item at the live layer):
1. **All 9 S0 findings are closed live:**
   - F-01: drilled restore with timing; deletion protection on;
   - F-02: the publish path refuses `/curate/`, and an absence probe confirms it;
   - F-03: honest dispute notice, email channel and response times;
   - F-096 and F-183: fixture pages corrected;
   - F-097 and F-131: no personal handle in any public id; the old→new map is restricted;
   - F-130: the API answers an honest "scope not available";
   - F-387: attribution is correct in downloads, the API and the map, behind a publish-time gate.
2. **Alerts reach the operator.** A test alert has been received. The budget alert at $300 and the billing export are live.
3. **CI is pinned before 2026-10-19.** Every boundary read head-bound CI, and no row advanced on red.
4. **Memory:**
   - M1–M10 run in CI;
   - 0 pending transitions from SEED-14;
   - 0 G1/G2 violations in 11A commits.
5. **G2 step 1 is live,** and the 10-10 replay was read back first.
6. **The quality baseline reproduces L2** (29/45 failing) in ratchet mode. GQ-20, GQ-24 and GQ-27 are `enforce`, with 0
   ratchet regressions.
7. **Live probe:** 0 instances of "human-verified", "counsel", "editorial board", "one-click" or "anonymous" outside
   disclosed contexts (G2 §6).
8. **The live-leg queue holds no leg whose window has opened.**

**Releases and operator touchpoints:**
- republish #1 and republish #2 (in-ticket gos, with copy batches under B-2);
- the P34.46 go, with the operator available in the slot;
- GATE-G4.

### 4.2 11B — Correct and traceable (P35, rows 249–313, 62.5 runs)

**Contents.**
- **Ops truth first:** the scheduler of record and cron lint (P35.1), alerts as code (P35.2), production-truth probes
  (P35.3), the runbook (P35.4).
- **The zero-egress host** (P35.5): the F-386 decision row and the kill switch.
- **Wave A:** P35.6–P35.11, live 10-19→10-23.
- **Release identity:** P35.12–13.
- **F5 data fixes:** vocabulary and entity typing, technology typing, geometry (P35.14–16).
- **Placement:** JUR-01 → 02a → 02b (P35.17–19), then number derivations (P35.20).
- **The Stream-L identity core:** CONF-03a → 08 → 03b → 04 → 06 → 05 (P35.22–27).
- **The officer-naming gate:** P35.28.
- **Labels and `/network/`:** P35.29–30.
- **Transparency export layer:** P35.31–42, ending with a release id and pinned citation on every page.
- **Watch, contributions and dossiers at every level:** P35.43–45.
- **The dedup:** CONF-07a/b (P35.46–47).
- **The agent review lane and the OPCHECK protocol:** P35.48–49.
- **Page registry, budgets, and the tile fix for the vanishing dots:** P35.50–52.
- **The release pipeline:** REL-03a → 03b → 08 → 04a → 05 → 04b → 09 → 06 (P35.53–60).
- **G2 steps 2–3:** P35.61–62.
- **The first model release (P35.63).** It carries the dedup, labels, citations, tiles and four-level dossiers in **one**
  Class S readout.

**By theme (runs):**

| theme | runs |
|---|---:|
| data correctness | 16.5 |
| release ops | 13.5 |
| transparency | 10.5 |
| UX core | 10.5 |
| sources | 4.0 |
| safety | 3.0 |
| Round-10 activation | 3.0 |
| debt | 1.0 |

**Entry.**
- GATE-G4 is recorded, with the 11B OM-20 list.
- ING-GO-A has been given, or the Wave-A leg is queued.
- **B-24 is answered**; otherwise P35.17's capture is queued and P35.63 waits (§7.3).
- OP-11 and OP-09 are done, or their defaults are recorded.

**Exit** (measured on the promoted P35.63 release):
1. **P35.63 is promoted** under a signed HG-11 readout, with V1–V15 green and 0 waivers.
   - The live rollback rehearsal is done.
   - `/r/<pub>/` and release search are live.
   - nginx honours withdrawals.
   - The old GATE-G3 signature is superseded, not transferred.
2. **L3 identity/time/geography targets at `enforce`** (L2 baseline in brackets):

   | target | L2 baseline |
   |---|---|
   | 0 subject-key collisions | 5,278 |
   | 0 1970 edges; every edge dated or labelled "undated" | 98.8% undated |
   | 0 publisher-as-operator (`unknown` allowed) | 74.2% |
   | technology on 100% of site rows | 77.4% mistyped |
   | 0 axis swaps / 0 null-island points | 562 / 14 |
   | 0 undisclosed out-of-polygon points | 2,370 > 25 km |
   | `unresolved` is not a dossier | — |
   | 0 mixed-scheme dossiers | — |
   | exact claim repeats ≤ 1 % | — |
   | derivation census 100 % | — |
   | dossier counts ≤ 1.02× lineage roots, or ranged "possible duplicate" intervals if A-6 defaults | up to 2.25× |
   | contradiction recall 1.0 on the synthetic set | — |
   | byte binding 100 % for the sources re-run in P35.61 | 0 / 2.78M |

3. **Traceability:**
   - 0 UUID-only labels on `/network/` (non-organisation labels only if A-10 defaults);
   - every figure reaches its evidence in ≤ 2 clicks, or says why it cannot;
   - map tiles hold 100 % of sites at z ≥ 10;
   - the fixture-sentinel scan finds 0 hits.
4. **Wave A is live** (≈ 18k claims; statute layer 2026) with +0 re-runs and a coverage delta recorded.
5. **OPCHECK was performed** for P35.63, if Q-L3-3 = a.

**Releases and operator touchpoints:**
- ING-GO-A;
- the P35.61 go with its `--authority` scope;
- the P35.63 HG-11 readout (+ OPCHECK);
- GATE-G5, with the D-K2-1 top-50 organisation review due by then (OP-14, about 1–2 h).

### 4.3 11C — Explorable core (P36, rows 314–387, 65.0 runs)

**Contents.**
- **Collection conduct:** robots and opt-out (P36.1, before any new host is fetched).
- **Owed rights flips:** P36.2.
- **Wave B:** code (P36.3–11) and **activation with the second release** (P36.12; 10-26→11-05).
- **API rate limits:** P36.13, before search v2 is public.
- **The L4 marker** (P36.14) and **redaction** (P36.15).
- **The design system and IA kit:** P36.16–26.
- **The figure kit:** P36.27–28.
- **Identifiers:** P36.29–30.
- **Search v2:** P36.31–32, P36.38–40.
- **Basemap and map:** P36.33, P36.36–37.
- **Grouped dossier index and redirects:** P36.34–35.
- **Entity pages A and the Organizations hub:** P36.41–42.
- **Status lane and release cadence:** P36.43–44.
- **Sources & data:** source pages, the sources table, known issues, downloads, evidence anchors (P36.45–51).
- **Dossier sources explorer, downloads and template v2:** P36.52–57.
- **Watch, evidence and research queue:** P36.58–63.
- **Home, About and onboarding:** P36.64–65.
- **Snapshots and changes plumbing:** P36.66–67.
- **Per-source versions:** P36.68–69.
- **Second-release acceptance:** P36.70.
- **Search activation:** P36.71.
- **ACC-PLACES:** P36.72 promotes the core-surfaces Class S release.

**By theme (runs):**

| theme | runs |
|---|---:|
| UX core | 37.5 |
| transparency | 11.0 |
| sources | 9.5 |
| release ops | 2.5 |
| governance | 2.0 |
| data | 1.0 |
| safety | 1.0 |

**Entry.**
- GATE-G5 is recorded, with the 11C OM-20 list.
- ING-GO-B and the A-7 batch lines are answered or defaulted.
- D-K2-1 is reviewed or defaulted.
- The DNS move (OP-09) is done, or A-3's GCS path is recorded.
- The relevance set (OP-21) is written, or the agent fallback is used (B-28 b).

**Exit.**
1. **Wave B is live:** each Tier-1 source is live or dispositioned by its line.
   - The second activated release (P36.12) is promoted.
   - P36.70 has measured the rollback and withdrawal timings.
2. **P36.72 is promoted under HG-11, and every operator ask has a working page passing its K-row acceptance:**

   | ask | page |
   |---|---|
   | U-003.1 | basemap and map shell |
   | U-003.2 | entity pages A and Organizations |
   | U-003.3 | search v2 |
   | U-003.4 | country-grouped dossier index |
   | U-003.5 | dossier sources explorer |
   | U-003.7 | watch pages |
   | U-003.8 | evidence hub |
   | U-003.9 | sortable sources table with downloads and ground-truth links |
   | U-003.10 | source pages |
   | U-003.11 | research queue with human-readable handles |

3. **Journeys** A1, A2, A3, A4, J1, O1, O3 and O4 pass the agent walkthrough at 390 and 1440 px, recorded
   `agent-verified`.
4. **Search** resolves 55 jurisdictions, 20 cities and the top 25 vendor and agency names.
5. **Budgets and accessibility:** K0 budgets and axe pass on real data, and the facet-conformance harness is green.
6. **Cost controls:** API rate limits are enforced, and the kill switch and budget alert have been tested. Measured
   infra ≤ $300.

**Releases and operator touchpoints:**
- ING-GO-B;
- two HG-11 readouts (P36.12, P36.72);
- the P36.70 rehearsal (in-ticket under D-G3-3's default);
- GATE-G6, in the same sitting as P36.72 where possible.

### 4.4 11D — Explored and proven (P37, rows 388–455, 62.0 runs)

**Contents.**
- **Wave C:** OSM becomes the origin of the national ALPR layer (P37.1–2; 11-16→11-20; Q-23).
- **Evidence-store and security baselines:** P37.3–4.
- **Ingestion hardening:** P37.5.
- **Governance pages and rights hygiene:** P37.6–8.
- **Lifecycle and the promotion gate:** P37.9–10.
- **Source-ops tail:** P37.11–15, including the conditional SRC-03.
- **Dossier live captures:** P37.16, under HG-03.
- **Map acceptance work:** P37.17–20.
- **Access, entity pages B, overviews and the explorer:** P37.21–27.
- **Dossier networks and the in-place map:** P37.28–29.
- **Watch predicates, lane and feeds:** P37.30–34.
- **Queue campaigns:** P37.35.
- **Raw archive and claim viewer v2:** P37.36–37.
- **Disagreements, quality basis, changes, API parity and search export:** P37.38–43.
- **Mechanical evaluation, `/quality/` and organisation identity:** P37.44–46.
- **Wave D, conditional:** P37.47–54.
- **Deposits and WACZ:** P37.55–56.
- **Projection rebuild and schema conformance:** P37.57–58.
- **Intake, dark and conditional:** P37.59.
- **Visual regression:** P37.60.
- **T1 enhancements and the contribution path:** P37.61–62.
- **Map and explore acceptance:** P37.63–64.
- **TX-16 final Class S release:** P37.65.
- **Coverage closeout, the Stream-L re-measure and CAP-01 journeys:** P37.66–68.

**By theme (runs):**

| theme | runs |
|---|---:|
| UX explore | 17.5 |
| sources | 14.0 |
| UX core | 8.0 |
| data | 5.0 |
| transparency | 5.0 |
| debt | 4.5 |
| release ops | 3.0 |
| Round-10 activation | 3.0 |
| governance | 2.0 |

**Entry.**
- GATE-G6 is recorded, with the 11D OM-20 list.
- ING-GO-C, Q-23 and the I8-Q5 Wave-D scope are answered or defaulted.

**Exit** (also the inputs to P38.1):
1. **All 13 journeys pass** the agent walkthrough and the operator walkthrough on P37.65.
2. **D3 §3 holds** on the final release (§8.1).
3. **CONF-14 re-measures L2:** every L3 round target is met, or each miss names its fixing row.
4. **Coverage (ACQ-28):**
   - the national ALPR layer comes from its origin;
   - every US state and DC has a dossier;
   - Flock, Axon and Motorola/Vigilant are entities with dated, sourced agency links;
   - all 154 Tier-1 and widening candidates are live or dispositioned;
   - 40 of 51 states + DC and 28 of 29 technology classes are verified live;
   - 11–12 of 14 I1 blind spots have moved.
5. **`/quality/` is live** with every check.
6. **Measured infra ≤ $300**, and the projection at 100× traffic is ≤ $300 or approved.

**Releases and operator touchpoints:**
- ING-GO-C, the tier-bump go, and ING-GO-D if Wave D runs;
- the P37.65 HG-11 readout;
- the CAP-01 walkthrough and gallery (OP-22).

### 4.5 Round tail (P38, rows 456–462, 5.0 runs)

| row | what | size |
|---|---|---|
| P38.1 | **CAP.1 (CAP-lite)**: an independent gap analysis of the landed rows against the Round-11 requirements; composed live verification, with CI for every open PR and probe-run records ≤ 24 h old; the two-sum headline per status layer (MEM-10's contract; B-5 vocabulary) | M |
| P38.2 | **CAP.3**: closes small in-scope gaps; everything else becomes a DEFERRALS row with a trigger. Assembles the accepted-deviations list, including **every descope caused by a decision default** | S |
| GATE-ACCEPT-R11 | the operator signs the accepted-deviations list verbatim (HG-14 domain). The Round-10 id `GATE-ACCEPT` exists, hence the suffix | — |
| P38.3 | **REC (one row)**: `reconcile-build` backlog + readiness, spec reconciliation and the integration plan. T3 splits it a/b if the working set overflows | L |
| P38.4 | **DOC (one row)**: `refresh-repo-docs` then `agent-docs`. Every statement about production cites a probe-run record (SK-20) | M |
| P38.5 | **CAP-02**: the announce-readiness review against D3 §5 (§8.3) | S |
| GATE-ANNOUNCE | the operator's decision; never automatic; agents contact no one. The announcement itself is LATER-22 | — |

---

## 5. Ordering and calendar

### 5.1 Fixed dates (UTC; G1, G2, G3, I8, H2; `date -u` today = 2026-10-01T01:00Z, Thursday)

| when | event | effect on the plan |
|---|---|---|
| 10-01 → 10-21 (06:09Z) | 32 first fires of existing triggers (peel-on 10-29 12:00Z) | watch only. P34.39 reads them back through the queue |
| **10-06 00:00Z → 10-13 12:00Z** | AR-3 batch window. **10-10 03:35Z** OSM replay (camreg batch-05) | no hosted DB write, schema change or job roll. QA metadata actions and web-bucket republishes are allowed outside 03:00–10:00Z |
| ≥ 10-10, after the replay ends | D-P31.4-1 read-back (P34.39, clock-guarded) | prerequisite of P34.46 |
| **≥ 10-14 14:00Z** | earliest Round-10 schema deploy (P34.46), then a 48 h soak | gates P35.11 and P35.61 |
| **before 10-19 00:00Z** | `ubuntu-latest` → Ubuntu 26 | P34.1 must have landed (row 201) |
| **10-19 (Mon) → 10-23**, 14:00–20:00Z | Wave A (P35.11) | ING-GO-A |
| **10-26 → 11-05**, one family a day | Wave B (P36.12) | ING-GO-B; Class S |
| **11-06 → 11-13 12:00Z** | AR-3 | no cuts. The core-surfaces cut (P36.72) is ≥ 11-13 12:00Z |
| 11-15 14:00Z | G3 monthly cut slot (REL-07 automates it after P36.44) | — |
| **11-16 → 11-20** | Wave C (P37.2): pre-grow and temporary tier bump | ING-GO-C, Q-23, tier-bump go |
| **11-23 → 12-04** (not 11-26), **12-14 → 12-18** (not 12-15) | Wave D, conditional (P37.54) | sources from the second window ship in the 2027-01-15 cadence cut, not in P37.65 |
| **12-06 → 12-13 12:00Z** | AR-3 | P37.65 is cut before 12-06 or after 12-13 12:00Z |

**Tokens used in `window_constraints`:**
- **AR-2:** an on-demand backup and a pre-state capture before any hosted write.
- **AR-3:** none of the three windows above; never 03:00–06:30Z daily; preferred slot 14:00–20:00Z on weekdays.
- **AR-4:** clock-guarded read-backs.
- **PUB:** republishes outside 03:00–10:00Z. A release cut never starts inside an AR-3 window (G3 §7.2).

### 5.2 Critical paths

- **Calendar (binding).** GATE-P → seed → GATE-B → P34.1 (by 10-19) → P34.39 (after 10-10) → **P34.46 (≥ 10-14)** →
  48 h soak → P35.11 Wave A (10-19→23) → 11B correctness and release chains → **P35.63** →
  P36.12 Wave B (10-26→11-05) → AR-3 → **P36.72 (≥ 11-13)** → P37.2 Wave C (11-16→20) →
  **P37.65 (outside 12-06→13)** → P37.68 → P38 → GATE-ANNOUNCE.
- **Run count.** S1a's longest seed→R11 chain is 21.2 runs (SEED-00 → … → CAP-02). Inside 11B, the longest runs are:
  - JUR-01 → 02a → 02b → DSRC-01 → JUR-03 → P35.63;
  - CONF-03a → 03b → 04 → 07a → 07b → P35.63;
  - REL-01 → 02 → 03a → 03b → 08 → 04a → 05 → 04b → 06 → P35.63.

  They converge on P35.63 by construction.
- **Decision path.** B-24 (boundaries) must be answered before P35.17, or the jurisdiction chain and P35.63 stall
  (§7.3).

### 5.3 How the chain behaves around the windows

Engineering outruns the calendar: Round 10 landed 35 PRs in 44 h (B5). So:
- every windowed live leg is a separate, queued step (OM-19);
- code rows keep flowing;
- the chain pauses only where a later row needs a queued leg's *live result* (marked `live:` by T3), or at a GATE.

Example: if 11A's code finishes before 10-13 12:00Z, P34.21's backfill and republish #2 wait in the queue. P34.22 onwards
continue, and the queue runs the leg at the first boundary after the window closes.

### 5.4 Expected timeline (inference; it slips one-for-one with R0)

**Assumptions:**
- S3 → S5 by about 10-03, and the seed by about 10-06 (R0);
- 6–10 runs a day, including CI waits;
- operator answers within a day of each pause.

**Expected:**
- 11A ends about 10-15 to 10-17, bounded by P34.46;
- 11B ends about 10-27 to 10-30;
- 11C's engineering ends about 11-05 to 11-08. Its release waits for 11-13 12:00Z, so GATE-G6 is about 11-13 to 11-16;
- 11D ends about 12-02 to 12-05, with Wave D's first window inside it;
- the tail ends about 12-05 to 12-10.

**Total:** about 9–10 weeks from R0. Without the windows, engineering alone would take about 4–6 weeks.

### 5.5 Ordering rules applied inside each sub-round

1. Rows with deadlines and safety come first: P34.1/2, then P34.3–6.
2. Guards come before the records they guard: P34.7–9, before the republishes and restorations.
3. Content comes before the republish that ships it (CF-12).
4. Code-only rows sit before freeze-bound hosted writes. The hosted writes come after 10-13 12:00Z in 11A's order.
5. Spine writes come before the freeze and candidate (P35.14–46 → P35.61 → P35.62 → P35.63).
6. Foundations come before pages: P36.16–30 before P36.34+, following K13 §7.4.
7. Every source activation comes after its rights lines and the robots register (S2 edge P36.12 ← P36.1).
8. Each release-promoting row is the last engineering row before its acceptance row and GATE, so one sitting covers both.

---

## 6. Manifest mapping (for T3)

- **Banner and phases.** A Round-11 dispatch amendment and banner name:
  - P34 = 11A "Safe, honest, truthful";
  - P35 = 11B "Correct and traceable";
  - P36 = 11C "Explorable core";
  - P37 = 11D "Explored and proven";
  - P38 = round tail.

  One appended `## Plan extensions` line records the round, its sub-rounds, gates and tail. Nothing above it is edited.
- **Rows.** 201–462 in physical order. Ids are `P3x.n`; gate rows take no `.n`, as Round 10's row 195 GATE-ACCEPT did not.

  | kind | rows |
  |---|---:|
  | ticket | 248 |
  | capstone | 7 (three acceptance rows, CAP.1, CAP.3, CAP-01, CAP-02) |
  | gate | 5 |
  | reconcile | 1 |
  | docs | 1 |
  | **HUMAN rows** | **0**: no external humans, and the operator's own work is a prerequisite or a gate item, never a chain row a ticket silently waits on (L3; B3 "nextTicket is never a HUMAN marker") |

  Non-chain kinds used only in the CSV are `seed`, `operator` and `later`. The 23 operator actions go in the manifest's
  `## Human prerequisites` section, each with its due point (CSV `sub_round`), and appear in the preceding check-in
  packet.
- **Gates.** GATE-G4 (row 248), GATE-G5 (313), GATE-G6 (387), GATE-ACCEPT-R11 (458) and GATE-ANNOUNCE (462). HUMAN-H6…H8
  stay reserved for the T-EVAL-IND segment (L3 §6.5).
- **Rows 184–187** (HUMAN-H4, P32.22a, HUMAN-H5, P32.23) become `marker` rows in the CSV. T3 appends L3 §6.3's tokens
  byte-for-byte:

  | row | token |
  |---|---|
  | 184 | `superseded-by(T-EVAL-IND segment: EV1, HUMAN-H6, HUMAN-H7)` |
  | 185 | `…EV-F` |
  | 186 | `…HUMAN-H8` |
  | 187 | `superseded-by(CONF-02 = P34.45, CONF-09 = P37.44; decision leg: T-EVAL-IND …)` |

  Validator V2 skips them. D-R10-HUMAN-1 stays OPEN and non-blocking, with trigger **T-EVAL-IND**: two or more independent
  labellers plus an operator contact exception to U-011. If the validator change is unwanted, use L3's alternative token
  `deferred(D-R10-HUMAN-1; T-EVAL-IND)`.
- **Round-10 return passes re-homed:**

  | Round-10 row | Round-11 row |
  |---|---|
  | 183 | P35.61 (ACT-14) |
  | 188 | P35.62 (ACT-15) |
  | 191 | P35.63 (ACT-24) |
  | 179–182 | P37.16 (ACT-22) |
  | D-P32.16-1 | P37.59 (ACT-23, conditional) |

  The GATE-G3 signature (row 190) does **not** transfer: P35.63 needs a new candidate-specific HG-11 readout.
- **`nextTicket` at seed:** row 201 = **P34.1** (R11-CI-01, TC-PIN). It has no dependency and a hard 10-19 deadline, and
  it makes every later CI result reproducible. This is B3's option N1. Under the A-13 fallback (CF-01) it is P34.0a.
- **T3 instructions:**
  1. Split SEED-13 (T3, 4 runs) into **T3a (P34–P35)** and **T3b (P36–P38)**, each sized for one context.
  2. Split the 15 L rows a/b (CF-16).
  3. Give every live-stage contract a `Live window:` header and an OM-14 mutation list.
  4. Mark live-result edges `live:`.
  5. Write full contracts for every row whose body is settled at GATE-P. Write `Kind: skeleton` contracts (BM-TICKET-03)
     only for the conditional rows (P37.12, P37.47–54, P37.59), which are filled after their gate lines.
  6. At each sub-round GATE, run `decompose-spec mode=extend` with a Phase-4 sizing review of the next phase
     (append-only).
  7. Add `harness:` to the template header (CF-04).
- **Tail shape:**
  - per sub-round, one acceptance row;
  - for the round, P38 = CAP.1 (M), CAP.3 (S), GATE-ACCEPT-R11, REC (L, 1 row), DOC (M), CAP-02 (S) and GATE-ANNOUNCE;
  - stream acceptances (P37.65–68) and MEM-10's contract feed CAP.1;
  - every tail row carries the `(live-read)` acceptance criterion.

  Compared with Round 10: 7 tail rows / 5 runs, against 9 rows; and live reads by construction, against 0.

---

## 7. Operator touchpoints and decision defaults

### 7.1 Where the chain pauses

- **Five gate markers:** G4, G5, G6, ACCEPT-R11 and ANNOUNCE.
- **Eleven in-ticket pauses:**

  | rows | what |
  |---|---|
  | P34.17, P34.21 | republish gos |
  | P34.46 | spine schema |
  | P35.11 | ING-GO-A, unless given at G4 |
  | P35.61 | bounded apply |
  | P35.63 | HG-11 |
  | P36.12 | ING-GO-B + HG-11 |
  | P36.70 | Class S under D-G3-3's default |
  | P36.72 | HG-11 |
  | P37.2 | ING-GO-C + tier bump |
  | P37.65 | HG-11 |

  P37.54's ING-GO-D is collected at G6.
- **Batching.** Several pauses share a sitting:
  - G4 + ING-GO-A;
  - P35.63 + G5 + ING-GO-B;
  - P36.72 + G6 + ING-GO-C/D;
  - P37.65 + CAP-01 walkthrough + GATE-ACCEPT-R11.
- **Under OM-20, the 84 production-touching rows need no per-row go** (11A: 20, 11B: 25, 11C: 13, 11D: 26). Without OM-20
  they would add up to 84 pauses.

### 7.2 What each sub-round pre-authorises (OM-20)

- **11A, at GATE-B:** QA actions, the drill clone, the attribution backfill, the clone rehearsal, LB/nginx (dark), IAM,
  the execution host and logins, the nightly quality job, and the ER re-run.
- **11B, at G4:** scheduler and fleet hygiene, the alert roll, the zero-egress host, typing and geometry backfills,
  re-keying and rematerialisations, the ingest-report table, the release bucket and staging, the API roll, the dark
  cutover, and the staged candidate.
- **11C, at G5:** rate limits, the basemap host, the status and cadence jobs, history backfills, and mirror writes.
- **11D, at G6:**
  - evidence-store and security config;
  - scheduler changes (SAM.gov, canary);
  - capture runs under answered HG-03 lines;
  - re-ingests and detector runs;
  - the raw-archive write;
  - the API roll;
  - WACZ.

### 7.3 Defaults that stall or descope

S3 should show each of these beside the criterion it disables. S5 should consider moving the stall ones into Part A.

| default (S1c line) | what it does to the plan | kind |
|---|---|---|
| **B-24** (D-K4-1, HG-03 boundaries) → "no" | P35.17 cannot capture boundaries, so P35.19 and P35.45 stall, and P35.63 waits (K13 §7.4: no immutable release with bare-code collisions). 7 jurisdiction S1s stay open | **stall — move to Part A** |
| **Q-23** (B-11) → cap 25 GB, "Wave C waits" | P37.2 stays queued. There is no national ALPR origin, and D3 §3(b) fails | descope |
| **A-7** → nothing flips | Waves B and C activate nothing. I8/D3 coverage criteria fail | descope |
| **A-13** → records-only seed | The seed PR may be red on the six pins (B4 NEW-3); rows renumber +2 (CF-01) | risk |
| **A-12** → three islands only | Rows flagged A-12-dependent (8) are re-scoped. U-003.2/.3/.6 are only partly met | descope |
| **A-10** → organisations withheld | Organizations is hidden and J2 fails. Entity, graph and network rows (11) ship non-organisation types only | descope |
| **A-3** → no DNS move | GCS basemap (+$4–41/mo); no public download links, so U-003.9/.10 downloads and J1's "rows in ≤ 3 clicks" fail | descope + cost |
| **B-30** (D-K3-5) → "no" | The search v2 API is staged, not rolled; U-003.3 is unmet | descope |
| **D-J3-6** (B-19) → "no" | `/s/` snapshots are not published, so J4 cannot pass | descope |
| **D-J3-11** (B-19) → "no status lane" | P36.43 is built but not scheduled; no ingestion heartbeat | descope |
| **D-G3-3** (B-9) → no standing go | Every release is Class S. More signatures, and P36.70 cannot rehearse a Class R | load |
| **D-J3-1** (B-19) → no raw bytes | P37.36 is built but not exposed | descope |

### 7.4 Operator time (inference; S1c §7 figures)

| when | items | time |
|---|---|---|
| Stage B | OP-01, OP-05/07, OP-18, GATE-B | ≈ 1.5 h |
| 11A | two republish gos + copy batches, the P34.46 slot, G4 | ≈ 2–3 h |
| 11B | DNS move, OP-11, ING-GO-A, P35.61, P35.63 + OPCHECK, the D-K2-1 top-50 review, G5 | ≈ 3.5–5 h |
| 11C | ING-GO-B, two readouts, the relevance set, G6 | ≈ 2–3 h |
| 11D + tail | ING-GO-C/D + tier bump, the final readout, journeys walkthrough, gallery, ACCEPT, ANNOUNCE | ≈ 3–5 h |
| **total** | | **≈ 12–18 h over ≈ 9–10 weeks** |

---

## 8. Success criteria

### 8.1 Round level

These criteria are the round's acceptance inputs, checked by P38.1 on the final release. Each is a live or public
measurement; where an answer is a default, the criterion is reported as "not attempted (default <line>)", never as
"MET".

1. **Features and UX (U-007a; D3 §3a):**
   - all 13 journeys pass both walkthroughs, agent and operator;
   - U-003.1–.11 pass their K-row acceptance live;
   - 0 UUID-only labels and 0 undated edges;
   - every figure reaches its evidence in ≤ 2 clicks, or says why;
   - search covers 55 jurisdictions, 20 cities and the top 25 vendor and agency names;
   - K0 budgets and accessibility pass on real data.
2. **Correctness and comprehensiveness (U-007b; D3 §3b):**
   - L3's round targets hold on the final release (CONF-14: the identity, time, geography, dedup, contradiction, byte-binding
     and attribution targets in §4.2), plus M-1b lower bound ≥ 0.98 per declared namespace and `/quality/` live;
   - the coverage targets in §4.4.
3. **Clarity (U-007c; D3 §3c):**
   - §1 is above the fold;
   - the home page is ≤ 5 screens at 390 px, with ≤ 6 figures;
   - 0 internal ids in prose;
   - the K14 design system and dark mode cover every template;
   - each persona has a "start here" path;
   - a fresh agent can say what SIG is in 2 minutes;
   - "beautiful" is the operator's call (B-29).
4. **Honesty metrics:**
   - 0 S0 open;
   - 0 status words unbound to recorded state (G2 §6);
   - 0 "verified/certified/counsel/editorial board" claims without basis;
   - PROVISIONAL on every unevaluated figure;
   - disclosure ships in the same publish as exposure (AR-6).
5. **Build truth:**
   - every boundary read head-bound CI;
   - 0 G1 (future-dated) and 0 G2 (append-only) violations;
   - every live leg was executed in its window or re-scheduled with a date;
   - every acceptance statement about production cites a probe-run record no older than 24 h;
   - no proxy signature;
   - at most 1 orchestrator close-repair (OM-02).
6. **Cost:** the measured monthly infra bill stays ≤ $300 every month; the 100× traffic projection is ≤ $300 or approved;
   agent spend is reported each sub-round.

### 8.2 Per sub-round

See the exit lists in §4.1–§4.4. Each acceptance row (P34.47, P35.64, P36.73) checks its own list at the live layer.
P38.1 checks §8.1.

### 8.3 Ready to announce (GATE-ANNOUNCE; never automatic)

P38.5 (CAP-02) prepares the D3 §5 checklist with evidence:
- [ ] the operator's own test: "I would send this to a journalist today";
- [ ] every S0 closed live, and status words bound to recorded state;
- [ ] all 13 journeys pass both walkthroughs;
- [ ] D3 §3(b) holds live;
- [ ] the attribution gate and the Part VIII screens are green, and forbidden-terms sources are withdrawn;
- [ ] a pinned citation and release id on every page;
- [ ] zero-egress serving, with the kill switch and budget alert tested;
- [ ] cost at 100× traffic ≤ $300, or approved;
- [ ] backups, a drilled restore and alerts;
- [ ] the dispute email discloses single-maintainer response times;
- [ ] §1 text, a known-issues page and the PROVISIONAL disclosures are live;
- [ ] **the dedup is published** (B-26);
- [ ] the gallery is signed (B-29);
- [ ] the About text is written by the operator (C-5);
- [ ] the operator confirms the announcement copy.

**The decision.** The operator's answer at GATE-ANNOUNCE is the decision. If unanswered, SIG is not announced. Agents
contact no one; the announcement is LATER-22, posted by the operator (U-009, U-011).

---

## 9. Budget plan

### 9.1 Monthly infrastructure by sub-round

Deltas are S1a's upper ends; the baseline is G1's unverified list-price estimate. C-7, or the 11A billing export,
replaces it with real numbers.

| after | delta this sub-round | items (USD/mo) | cumulative delta | projected total |
|---|---:|---|---:|---:|
| baseline | — | Cloud SQL ≈ 52–54, LB ≈ 18, `sig-api` min-1 ≈ 7–10, jobs ≈ 3–9, rest | 0 | ≈ 90–100 |
| 11A | +4.90 | quality job 2, alerts 1 (Track 0.5 included), Round-10 API 1, logical export 0.5, data protection 0.3, cost guard 0.1 | +4.90 | ≈ 95–105 |
| 11B | +1.19 | zero-egress host 1, Wave A 0.5, release bucket/staging 0.5, regression corpus 0.05, candidate 0.04, release 0.1; AR cleanup −1 | +6.09 | ≈ 96–106 |
| 11C | +14.70 | **optional Cloud Armor 6**, release cadence 4 (monthly cut writes + weekly materialise), Wave B 2.5, basemap on R2 2, status lane 0.2 | +20.79 | ≈ 111–121 |
| 11D | +11.90 | security baseline 5 (log volume unmeasured), Wave C 2.2 (incl. +1.7 disk pre-grow), conditional intake 2, conditional Wave D 1.5, evidence store 0.5, WACZ 0.2, keyed 511 0.2, canary 0.1, watch lane 0.1, raw archive 0.1 | +32.69 | ≈ 123–133 (+≈ 1 domain) |

**Scenarios:**
- **A-3 = b (no DNS move):** GCS basemap ≈ $6–43 instead of ≈ $2, and no public download links (so ≈ $0 egress). The
  round ends at ≈ $127–174.
- **B-30 = a:** +$3 (search API memory) from 11C.
- **Defaults that remove cost:** I8-Q5 b (no Wave D) −1.5; B-8 a (no intake) −2; Cloud Armor declined −6.
- **Later triggers:** LATER-08 permanent Cloud SQL tier +$49 → ≈ $172–182; optional HA ≈ +$50 more.

### 9.2 One-off costs

| item | cost |
|---|---|
| restore drills | ≈ $0.15–0.40 each (P34.6; monthly logical export thereafter) |
| Wave-C temporary tier bump | ≈ $3 |
| Class S release object writes | ≈ $2.5 each × about 6 ≈ $15 |
| `sig-project.org` | ≈ $10–20/yr (OP-11) |
| optional hardware signing key | ≈ $25–55 (A-16) |
| paid data | $0 (B-12) |

### 9.3 Items needing the operator's approval

**None of the planned items goes above $300/mo.** The watch list, read at every check-in:
- **Denial of wallet.** `sig-public` stays world-readable until the P35.5 kill switch (≈ $120/day at 1 TB/day; G1 §3.8).
  P34.5's budget alert sees it but does not stop it.
- **Abuse of the search API** before P36.13 (≈ $140/mo worst case; S1c).
- **Download egress** if A-3 = b *and* links were exposed. This is blocked by P36.50's default.
- **LATER-08.**

### 9.4 Cost truth

- **P34.5** adds the billing export and the "visible spend ledger" (U-011).
- **From the first acceptance row**, every check-in shows **measured** month-to-date spend and the forecast, not
  estimates.
- If the measured baseline is well above G1's estimate, G4 re-projects the round before 11B begins.

### 9.5 Agent (build) spend transparency (A-2: the ceiling covers infrastructure only)

**Volume.** About 262 chain rows, about 15 rows from T3 splits, an estimated 15–25 live-leg re-runs, the seed's 23.2
runs, and the orchestrator sessions. That is about **300–330 fresh worker contexts**, or about 1.1–1.3 per row on
Round 10's experience (inference).

**Each acceptance row reports:**
- the worker runs dispatched, re-runs and splits;
- the harness and model (OM-01);
- usage-limit events (the planning session already hit one at about 19:10Z on 09-30);
- dollars, where the operator's plan exposes them.

**Limits.** No new paid model service or second model family without an explicit go (OD-02 default a; Q-L3-4 default
no). No figure is invented: "not measured" is a valid line.

---

## 10. Risks and mitigations

| # | risk | mitigation |
|---|---|---|
| R-1 | **Live legs never run.** This is Round 10's "7/7 return passes prepared, not executed", in queued form | OM-19 runs due legs at every boundary. A GATE cannot be presented while an opened window is unexecuted, and acceptance rows read the queue. "Engineered" is never reported as "live" (OM-06) |
| R-2 | **Defaults stall the critical path** (B-24) or silently descope operator asks (§7.3) | Move B-24 to Part A. S3 shows each default beside the criterion it disables, and P38.2 lists each one as an accepted deviation |
| R-3 | **Scale.** About 277 rows after splits; CAP-01 depends on about 110 rows; fan-in seams | Four Round-10-sized phases; sizing re-checked at each GATE; the re-split rule (§3.2); T3 split into T3a/T3b |
| R-4 | **Operator load and approval fatigue at night** (B5 §5) | 16 pauses, batched into about 5 sittings; OM-20; B-2's removal-only allowance; readouts from P35.60's generator; activation slots at 14:00–20:00Z on weekdays; agent text confirmed against its sha256 prefix (OM-07) |
| R-5 | **Hosted-write accidents.** L44 rewrites `claim_evidence` under an exclusive lock; re-keying; backfills; Wave C's ≈ 1.1M claims on 1 vCPU | AR-2 restore points; the P34.6 drill first; the P34.24 clone rehearsal; P34.46 and P35.61 are never pre-authorised; AR-3 windows; the temporary tier bump; one manual job at a time |
| R-6 | **Denial of wallet** before the P35.5 kill switch | P34.3 makes `sig-web` non-public; the P34.5 budget alert; P35.5 early in 11B; the measured-spend watch at every check-in |
| R-7 | **The UX outruns the data** (K13 R-1) | Correctness first: all of Stream L's S1 fixes are in 11B, before any new surface. Capability binding. CAP-01 checks for wrong-conclusion risk |
| R-8 | **Calendar slip.** R0 later than 10-14 compresses Wave A behind P34.46, and an outage moves a window by a month | Windows are the earliest dates. The queue absorbs slips without idling the chain. I8's waves can each move to the next month, and Wave D is droppable as a whole |
| R-9 | **CI unavailable or flaky** (40 starts lost 09-17→22; Lighthouse flake) | P34.2's flake allow-list and one re-run (Q-H2-4). "CI unavailable" becomes `blockedOn`, with a verbatim, time-boxed waiver only (H2 §6) |
| R-10 | **Rights or legal exposure without counsel**: vendor terms, the database right, Part VIII | HG-03 lines per batch with "not flipped" defaults; vendor hosts never fetched (A-17); P35.28 officer-naming gate before entity pages; P36.15 redaction before the evidence hub and raw archive; US-first (CF-06) |
| R-11 | **The public repo**: the first push publishes the planning notes, the operator's address and redacted Part VIII findings | B-16: keep local until T6, and scan before pushing (SEED-00). The seed PR is the first publication |
| R-12 | **A harness or model switch mid-round** | OM-01 and A-15: one harness, switches only at boundaries, with orient, validators and a CI read after a switch |

---

## 11. Hand-off to S3/S5

1. **Promote B-24 to Part A.** Its default stalls P35.17 → P35.63 (§7.3).
2. **Show the nine descoping defaults** next to the success criteria they disable. State §8.1's criteria as conditional on
   the recommended answers.
3. **Ratify OM-19 and OM-20, the check-in packet (§3.6), and the GATE-B pre-authorisation list** (an S5 operator line).
   Without OM-20, about 84 rows become pauses.
4. **CF-06 is a scope cut against I8** (ACQ-23a/b → LATER-09; Wave C US-scoped). CF-15 keeps RI-01 bundled. Either can be
   reversed at S5 through A-17 or B-3.
5. **A-1 still matters.** Track 0.5 covered alerting. The QA-9 drill before the 10-10 replay happens only if the operator
   grants it now; otherwise it is P34.6.
6. **S3/T4:** switch S1b's rule (c) to `sub_round ∈ {11A, 11B}` from this CSV (§2.2).
7. **T3:** use T3a/T3b, the a/b splits, `Live window:` headers, `live:` edges, skeletons only for conditional rows, and the
   A-13 fallback numbering.

---

## 12. Reproduction and checks

**The builder.** A scratch builder outside the repository (session scratchpad `s2/build_plan.py`, not committed, like
S1a's) reads:
- `data/ticket_catalog.csv`;
- `universe/UNIVERSE_DISPOSED.csv`;
- `tools/check_dispositions.py` (`first_waves()`).

It writes `data/round11_plan.csv`. **Results at render time:**
- 0 errors;
- 262 chain rows (201–462);
- kinds: ticket 248, capstone 7, gate 5, reconcile 1, docs 1;
- runs by sub-round: 11A 44.0, 11B 62.5, 11C 65.0, 11D 62.0, tail 5.0;
- **every one of the 317 catalog units placed exactly once.** LATER-01 also names the four 184–187 markers. ACQ-23a/b
  appear as `later`;
- **0 order violations** over the catalog edges and the 24 S2 edges (`(S2)` in `depends_on`). The only non-chain edges
  are the two `→dropped(CF-06)` entries on P37.54, which are intended;
- the S0/S1 owner closure is **76 units, all in 11A ∪ 11B**;
- 15 L rows; 11 in-ticket pauses; 84 production-touching rows (11A 20, 11B 25, 11C 13, 11D 26); 10 conditional rows
  (9.5 runs).

**CSV columns.** `row, id, cat_ids, title, sub_round, phase, kind, depends_on, operator_gate, live_stage, est_runs,
window_constraints, notes`:
- `operator_gate` gives `<dec ids> [<S1c packet line>] -> default: <…>`, `named mutation (A-15)` with its OM-20 list, or
  `IN-TICKET PAUSE`;
- `notes` carry the size, the S0/S1 findings owned, interim duties, the S2 edges and conflict ids, the `A-x-dependent`
  flags, the cost delta, and S1a's `where_it_must_land`.
