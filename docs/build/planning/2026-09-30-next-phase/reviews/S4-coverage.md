# S4 adversarial review — coverage and traceability lens

- **Artifact reviewed:** `NEXT_PHASE_PLAN.md` (DRAFT, S3, written 2026-10-01T01:13:07Z → 01:26:35Z).
- **Reviewer:** fresh-context Claude Code (Opus 5.5) subagent, lens = coverage and traceability. I did not write the
  plan or any of its inputs. **Review run:** 2026-10-01T01:27:26Z → 2026-10-01T01:42:00Z (`date -u`).
- **Read-only.** This file is the only write. Nothing was committed, nothing outside this file was edited, and no
  external request was made.
- **Method (mechanical where possible).** `python3 tools/check_dispositions.py` → `OK (0 errors)`. Python/csv recounts
  over `data/round11_plan.csv` (333 rows), `data/ticket_catalog.csv` (317 units), `data/decision_catalog.csv` (323 ids),
  `universe/UNIVERSE_DISPOSED.csv` (1,159 items), `findings/FINDINGS.csv`, `data/owed_register_adjudication.csv` (F1),
  `docs/tickets/DEFERRALS.md` (97 rows, 36 owed) and `docs/build/COVERAGE_MATRIX.csv` (715 rows). Also: the transitive
  closure of the S0/S1 owner rows, a forward and reverse `depends_on` walk, and greps of the verbatim operator record
  (`feedback/OPERATOR_FEEDBACK.md`, META_PLAN §7/§7.1) against plan rows. PD-relative paths throughout.

## Verdict: **ratifiable-with-fixes**

The skeleton holds. The counts match the CSVs, every catalog unit is placed, the 36 owed deferrals all have a
disposition, and the S0/S1 owner closure really does sit in 11A ∪ 11B. But the plan's main protection against silent
descoping does not hold yet. That protection is §4.4 plus P38.2's rule "not attempted (default <line>)", and §4.3 calls
Part B "safe defaults". Two BLOCKERs must close in `reviews/REVIEW_CLOSURE.md` before S5:
- several defaults that disable operator asks are not listed (COV-01);
- a second critical-path stall is hidden in the authoritative CSV (COV-02).

Both fixes are bounded edits to §4.4/§4.5 and to `round11_plan.csv`. No restructuring is needed.

**Counts:** BLOCKER 2 · MAJOR 8 · MINOR 7.

## What checked out (so closure does not re-verify it)

- **Plan rows.**
  - 333 rows: 262 chain, 4 markers, 20 seed, 23 operator, 24 later.
  - Rows 201–462 are contiguous and unique.
  - Kinds: ticket 248 · capstone 7 · gate 5 · reconcile 1 · docs 1.
  - Runs: 44.0 / 62.5 / 65.0 / 62.0 / 5.0 = 238.5.
  - 10 conditional 11D rows = 9.5 runs. 11 in-ticket pauses, exactly the ones listed.
  - Gate rows are 248 / 313 / 387 / 458 / 462.
  - Theme rows and runs in §5 match the catalog's `theme` column exactly.
  - 24 S2 sequence edges; 0 order violations.
- **Universe.**
  - Disposition totals (739/146/153/41/26/24/14/8/7/1) and every per-kind count in §9.3/§9.6 match the CSV.
  - S0 = 9, S1 = 104.
  - The S0/S1 owner closure is 58 owner rows plus prerequisites, giving 76 chain rows (11A 37, 11B 39) and 78.0 runs.
    No closure row is in 11C/11D. Three operator actions (OP-05, OP-11, OP-18) are also in the closure.
- **Deferrals.** DEFERRALS.md has 32 OPEN + 4 PARTIAL, the same 36 ids as §9.2. Each matches its
  UNIVERSE_DISPOSED disposition, and all except D-SOURCES.8-1 (COV-07) are consistent with F1.
- **U-003 trace.** The §5.7 table equals the universe `disposition_ref` sets for U-003.1…11 and U-003.G (no row
  missing or extra), and the §9.5 first owners resolve correctly.
- **Not-MET requirements.** All 69 (54 PARTIAL + 10 MISSING + 5 AT-RISK) are universe items.
- **Catalog placement.** All 317 units appear in `round11_plan.csv`. The 252 r11 units split into 250 chain rows plus
  R11-ACQ-23a/b in `later`. Exceptions are in COV-13.

---

## BLOCKER

### COV-01 — §4.4's default→descope list is incomplete: several operator asks can be descoped silently by "safe" defaults

**What's wrong.** §0 (l. 61) and §4.4 (l. 316–335) promise that every default which stalls or descopes is "shown beside
the criterion it disables". P38.2 then reports such criteria as "not attempted", never MET. §4.3 (l. 301) presents Part
B as "42 batch lines with safe defaults". These defaults descope operator asks but are missing from §4.4. Several of
them are not wired to any plan row either, so P38.2 has nothing to report and the descope disappears.

| default (packet line → member) | what it disables | operator words it descopes | evidence |
|---|---|---|---|
| **B-19 → D-J3-2** (Q-22b) → "no run logs published" | Scrubbed run logs on the run export and on the source pages and table | Wave-2: *"see ingestion logs/metrics/timestamps"*; U-003.9 *"ingestion metrics and metadata"*; U-003.10 *"ingestion history"* | `data/decision_catalog.csv:106` (unblocks TX-03, TX-05, TX-07). No plan row reads D-J3-2: the `operator_gate` cells of P35.33 (l. 82), P36.47 (l. 161), P36.48 (l. 162) and P36.69 (l. 183) are silent (`grep D-J3-2 data/round11_plan.csv` → 0). §4.4 lists only the B-19 members D-J3-1/-6/-11 |
| **B-25 → D-K2-4** → "no" | 474,184 Flock share-list edges unused in overview builder B (P37.25) | U-007 *"rich, US nationwide data on Flock"* | `round11_plan.csv:213`; `decision_catalog.csv:117` |
| **B-31 → Q-L3-3/5/6** → "no checks; passing checks only; C0/C1 only" | No OPCHECK runs (P35.49). `/quality/` shows passing checks only (P37.45), which also breaks S2 11D exit 5 and §13.2 #2, "`/quality/` live **with every check**". C2 collapse is off (P35.46) | U-006/U-007 *"increased confidence in algorithms"* | `round11_plan.csv:98,233`; `decision_catalog.csv:126,128,129`; S2 `design/S2-round-structure.md:603` |
| **A-3's alias member** → "no alias" | OP-10 `contact@` alias (it depends on OP-09) | U-014 *"maybe we do want to set up a contact@ … email"* | S1c §2 A-3 "if unanswered … no alias"; `round11_plan.csv` OP-10 `depends_on=OP-09`. §4.4 row 5 lists downloads and basemap only |
| **B-11 → I8-Q5** → "core only" | Wave D (P37.47–54) recorded as dropped. Under Tier 1 alone, I7 projects 40 of 51 states, 13 of 36 thin cities and 28 of 29 classes, against 46, ≈ 20–25 and 29 with Tier 2 | U-007 *"expansion of high quality sources to maximal degree"* | `decision_catalog.csv:88`; `research/I7-candidates.md:674`. §4.4 row 1 shows only the 25 GB cap |
| **B-27 → D3-Q4** → "no peer links" | The accepted K12b idea I-24 (link-outs) and the §3.1 invariant "peers are linked, not rebuilt" | U-003.X (agent ideas, accepted) | `decision_catalog.csv:119`; K13 §5.2 I-24 |
| **B-28 → D-K3-7** → agent writes the held-out set | U-003.3's acceptance ("held-out ≥ 80 % top-3") is then measured on an agent-written set | U-003.3 | `round11_plan.csv` P36.32 gate |
| **B-18 → D-SOURCES.7-2** → "stay OPEN" | P37.12, keyed US 511 cameras, recorded as dropped | U-007 coverage | `round11_plan.csv` P37.12 gate |

**Fix.**
1. In §4.4, add one row per line above (default · kind · criterion · rows).
2. In `round11_plan.csv`, add `D-J3-2 [B-19] -> default: no run logs` to the `operator_gate` cells of P35.33, P36.43,
   P36.46, P36.47, P36.48 and P36.69, and state what each row publishes under that default.
3. Correct §4.3's "safe defaults" wording. Name B-19, B-25, B-27 and B-31 as descoping.
4. Consider promoting B-19 (Q-22, the operator's own Wave-2 ask) into Part A, the way B-24 became A-18.
5. Update §0's count ("nine") to match.

### COV-02 — Undisclosed second critical-path stall: P35.38 hard-depends on OP-11, whose default is "don't do it"

**What's wrong.**
- P35.38 (SAFE-06, identity base + crawler-contact truth) has `depends_on = P34.25;OP-11` (`round11_plan.csv:87`).
  OP-11 is "Defensively register sig-project.org" (l. 320), and its decision line Q-E2-03 [B-6] defaults to **"move only;
  no purchase without a go"** (`decision_catalog.csv:64`).
- P35.38's own gate cell says the default is "UA/contact URL moves to surveillancegraph.org, no purchase". The hard edge
  to OP-11 stays anyway.
- A reverse-dependency walk from P35.38 reaches **25 rows**: P35.39 → P35.47 → **P35.63** (first model release), P35.64,
  GATE-G5, P36.66–P36.73, GATE-G6, P37.40/41/65/67/68, all of P38, and GATE-ANNOUNCE.
- §0 (l. 61), §4.4 (l. 324) and §8.8 claim A-18 is the **only** stall.
- The same edge makes the S1 finding F-184's owner an operator purchase (OP-11, "by GATE-G4"), not a ticket.

**Fix.**
- Make the P35.38 → OP-11 edge conditional (`OP-11 (soft; only if B-6 = a)`). Alternatively, list B-6/Q-E2-03 as a
  stall in §4.4 and promote it into Part A.
- Rehome F-184 to P35.38 (SAFE-06), with OP-11 as a `links` entry.
- Re-run a reverse-dependency check over every chain-row edge into an `operator` or `later` row. Today there are three:
  P34.27 → OP-18, P35.38 → OP-11 and P37.12 → OP-13. Record each one's default behaviour in §4.4.

---

## MAJOR

### COV-03 — Operator asks recorded only in META_PLAN §7.1 are not universe items, so no checker can see them dropped

**What's wrong.** `tools/check_dispositions.py` builds the feedback universe only from U-ids in `OPERATOR_FEEDBACK.md`
(l. 148–150, 284–285), and rule (d) checks only U-003.1…11 (l. 21, 71, 423). As a result the following have no
`UNIVERSE_DISPOSED` row, no disposition and no mechanical check (`grep -c 'Wave 2' universe/UNIVERSE_DISPOSED.csv` → 0):
- The Wave-2 scope addition (META_PLAN §7.1):
  - *"configure them for ingestion and ingest them into prod"*;
  - *"making the data itself easily exportable"*;
  - *"explore each third party source"*;
  - *"link to the ground truth"*;
  - *"download the raw data"*;
  - *"see ingestion logs/metrics/timestamps"*.
- The 18:2xZ approvals (S0 hotfixes, QA-1…QA-10, `/task/new/` demo pages).
- GATE-M's *"keep me in the loop"*.

§9.5 ("Every operator feedback item") lists only U-ids. The asks are delivered in substance: QA-1…10 trace to
R11-ACT-01…04, `/task/new/` traces to R11-ACT-06 via F-278, and the export asks overlap U-003.9/.10. But the two most
default-exposed asks, raw data (B-19, A-3) and ingestion logs (COV-01), are exactly the ones nothing checks.

**Fix.**
- Add feedback items to the universe:
  - **W2-1…W2-6** for the six Wave-2 clauses;
  - **PF-1…PF-3** for the 18:2xZ approvals;
  - **GM-1** for "keep me in the loop".
- Quote each one verbatim from META_PLAN §7.1 and give it a disposition with its rows:
  - ingest into prod → P35.6–11, P36.12, P37.2;
  - explore each source → P36.45–49, P36.69;
  - ground truth → P35.35–36;
  - raw data → P37.36 + P36.50;
  - logs/metrics/timestamps → P35.32–33, P36.46, P36.43;
  - in the loop → OM-17 digests.
- Extend check rule (d) to these ids, and add them to §9.5 and §1.1.

### COV-04 — U-003's headline clause ("everything currently advertised should actually work") has no trace or acceptance

**What's wrong.** U-003 opens: *"A first-time user of SIG should be able to do all of the things currently advertised /
attempted on the current surveillancegraph.org deployment but the functionality should actually work the way a user
expects"* (`feedback/OPERATOR_FEEDBACK.md:31-33`).
- The universe disposes U-003 as `merged-into(U-003.G)`. U-003.G is the "friendlier, richer" ask, and its live check
  (≤ 6 nav sections, ≤ 2 actions to evidence) does not test advertised functions.
- No route-level acceptance exists. `grep -i 'advertised' design/K13* design/D3* design/S2* NEXT_PHASE_PLAN.md` → 0 hits,
  and `review/ROUTES.csv` (48 routes) is not referenced by any acceptance row.
- Several advertised functions are resolved by withdrawing or labelling them rather than making them work:
  - one-click dispute/correction: an honest notice (P34.17) + B-8 email-only; intake P37.59 stays dark;
  - `/contribution-back/`: LATER-03;
  - `/curate/`: removed;
  - `/task/new/` demo pages: stripped;
  - research-queue "send": drafts only.

Each of these is defensible under U-011/U-008/B-8, but the operator is never asked, as a class, to accept "withdraw
instead of fix".

**Fix.**
- Add to P36.72 and P37.68 a ROUTES.csv-driven check: every route advertised on the 2026-09-27 release either passes a
  user-expectation check or shows an honest notice naming its decision or LATER trigger.
- List the withdrawn-not-fixed features in §5.7.
- Add one S5 confirmation line (C-12 or D2) so the operator accepts that list in their own words.

### COV-05 — U-007's "rich, US nationwide data on Flock and Axon" is weakly traced; a D3 Flock criterion is dropped

**What's wrong.**
- **No Axon row.** `grep -ci axon data/round11_plan.csv` → **0**. Axon arrives only through the USAspending
  `recipient_search_text` slice and BWC ALN 16.835 in P35.9, which cover federal awards only (I8 l. 327), plus RTCC/Fusus
  council matters (I8 §9 #2).
- **Weak acceptance bar.** The acceptance is "Flock, Axon and Motorola/Vigilant exist as entities with dated, sourced
  agency links" (plan l. 508). A single link satisfies it.
- **Dropped criterion.** D3 §3(b) also requires *"OSM ALPR, Eyes on Flock and Atlas vendor data reach place and entity
  pages"* (`design/D3-product-direction.md:95`). That criterion is absent from §5.5's acceptance and from §13.2 #2, which
  points only at "the coverage targets of §5.5" (l. 1190). P38.1 therefore never checks it. Only GATE-ANNOUNCE's "D3
  §3(b) holds live" (l. 1232) catches it, at the very end.
- **Defaults compound it.** B-25 turns the Flock share lists off by default (COV-01).

**Fix.**
- Add a "Flock / Axon / other vendors" trace row to §5.5, naming the rows (P35.8, P35.9, P36.5–6, P36.11, P37.1–2,
  P37.25) and I8 §9's projected numbers as acceptance thresholds: Flock agency-origin layers in 14 agencies across 11
  states; the national ALPR origin; Axon agencies via procurement and council matters.
- Have P37.66 report per-vendor agency counts by state.
- Restore D3's criterion in §5.5 and §13.2 #2.
- State plainly in §5.5 that Axon facts are thin by design (vendor hosts never fetched), so the operator can weigh it at
  A-17.

### COV-06 — "Every S0/S1 … resolved in 11A ∪ 11B" counts interim mitigations and default-dependent owners as fixes

**What's wrong.** The owner closure is genuinely in 11A ∪ 11B, but for several S1s the owner row only labels or
mitigates the defect. The real fix lands later, depends on a default, or sits on a row that does not fix it.
- **F-07, F-099, F-390, F-399 (permalinks do not pin).** These go to P35.42 = TX-13a, whose scope is *"honest interim
  wording until /s/<pub>/ exists"* (`ticket_catalog` R11-K13-TX-13a). Actual pinning is P36.66 (11C), and its gate is
  *"D-J3-6 → default no: /s/ snapshots built, not published (J4 then cannot pass)"* (`round11_plan.csv:180`).
- **F-103 (bulk data, manifest and API not linked).** This goes to P34.13. P34.13 only re-points `/terms`; the bulk links
  are P36.50 (11C), and under A-3's default there are no public download links.
- **F-386 (bulk release unreachable).** This goes to A-3, and under the default it stays unreachable.
- **F-452, and F-106/F-420's labels.** These depend on A-10 (default: all organisations withheld).
- **F-522 (0 of 2.78 M bindings reach bytes).** The owner is P35.61, which binds only re-run sources. The plan's
  acceptance ("100 % for sources re-run in P35.61", l. 469) is narrower than L3's "every re-run source"
  (`design/L3-confidence-program.md:920`). The plan never says that the ~2.78 M legacy bindings stay zero-byte under the
  insert-only spine.
- **F-27 (validators check structure, not truth).** The owner is SEED-18 ("projection regenerate + seed PR opened"),
  which does not fix it. The fix lives in SEED-02 (guard core) and P34.9 (M2 no-vacuous-pass).
- **F-184.** Owned by OP-11; see COV-02.
- **§9.4 (l. 976).** It says 101 "land on a seed or 11A/11B unit", but that number includes F-184 → OP-11 and
  F-522 → a live-return-pass.

**Fix.**
- In §9.4, add a per-finding table for the S0/S1 items whose fix is partial or conditional. Columns: owner ·
  fix kind (fixed / interim / default-dependent) · final fixing row · default line.
- Rehome F-27 → SEED-02 (+ P34.9) and F-184 → P35.38.
- State F-522's legacy residual and the label it gets.
- Reword §0 (l. 50–51): "every S0/S1 has an owner or interim mitigation in 11A ∪ 11B; N are fully fixed only under the
  recommended answers to …".

### COV-07 — D-SOURCES.8-1's disposition contradicts the operator's US-first / no-counsel constraints

**What's wrong.**
- §9.2 sends D-SOURCES.8-1 (PARTIAL) to P36.2 via **B-41 "R4a–c flip"**. The remaining rows are `camreg_edmonton_ab`,
  `camreg_hk_hk`, `camreg_qldc_au` and `camreg_bellevue_wa` (DEFERRALS.md:160).
- E4-R4a–c recommend **flipping three non-US sources on a database-right basis** (`decision_catalog.csv:134-136`).
- **B-34 recommends the opposite.** B-34 / I7-N1 says non-US database-right lines are **not flipped this round**,
  *"because D3 does not expand non-US coverage and no counsel reviews the database right (U-013)"*
  (`decision_catalog.csv:171`).
- **The plan agrees with B-34 elsewhere.** It repeats that rule in §5.5 (l. 483–484) and ADR-169 (l. 789), and D3/CF-06
  say non-US dossiers are "corrected but not expanded".
- E4-R4a's own rationale says "decide … once the terms body is captured", yet it recommends **a**.
- F1's disposition predates D3 and B-34. The plan's precedence rule ("later synthesis wins") does not resolve a conflict
  inside S1c.

**Fix.**
- Align B-41 R4a–c with B-34: answer **b**, capture terms, not flipped.
- Redispose D-SOURCES.8-1 → `decision(E4-R4)`. Bellevue is declined under A-9. The three non-US rows go to
  `later-phase` with trigger "operator expands non-US coverage", folded into LATER-09/LATER-10.
- If the operator wants these flips anyway, carry them as an explicit, signed exception to B-34.

### COV-08 — Several ADRs are owned twice: by T1 (Stage B) and by a chain ticket

**What's wrong.** Appendix A T1 writes "one file per ratified decision in §7" (l. 1316). These catalog scopes also write
the same ADR:

| ADR | also written by |
|---|---|
| 148 | P34.30, R11-MEM-06: "ADR recording the split" |
| 151 | P34.1: "pinned-test rewrite + ADR" (CF-01, `round11_plan.csv:2`) |
| 161 | P35.12, R11-REL-01: "one ADR extending ADR-132" |
| 162 (descriptor v2 / snapshots) | P36.66, TX-13b: "descriptor v2 ADR" |
| 174 | P35.1, R11-OPS-03: "ADR superseding ADR-016/076" |
| 176 | P36.13, R11-OPS-06: "ADR for the exposure posture" |

ADR numbers are "provisional — T1 assigns them in ratification order" (l. 759), so a chain row writing its own ADR would
collide or duplicate. P35.1's scope also supersedes **ADR-016**, which appears neither in ADR-174's row nor in T1's
status-line list (l. 1318–1320).

**Fix.**
- Add an "author" column to §7 (T1, or a row id).
- For each pair, either drop the ADR from T1 or strike "ADR" from the catalog scope and contract.
- Add ADR-016 to ADR-174's supersessions and to T1's list.

### COV-09 — Production-mutation authority is traced to two different decision lines; S5-1…S5-4 have no defaults

**What's wrong.**
- **Two sources of authority.**
  - `round11_plan.csv` (declared authoritative, §8) encodes OM-20 on **49 rows** as *"named mutation (A-15 [A-15] ->
    default a): no per-step go; listed in the GATE-x pre-authorisation"* (`grep -c 'named mutation (A-15'` → 49).
  - The plan instead makes OM-20 an S5 line: S5-1 ratifies it and S5-3 is the list (§4.5, l. 339–344).
  - A-15's default is "same as rec." (§4.2 l. 294).
- **No defaults.** §4.5 gives none for S5-1…S5-4, although §1.3 requires "every open line … answered or explicitly
  defaulted" for GATE-P.
- **Consequence.** A contract generated from the CSV would cite A-15 as its authority. Silence on S5-1/S5-3 then reads
  as pre-authorisation, which contradicts OM-18 ("silence is never consent") and §3.3's "Without OM-20, about 84
  production-touching rows become in-ticket pauses".

**Fix.**
- Re-key those 49 cells to `S5-1/S5-3 → default: no pre-authorisation (in-ticket pause)`.
- Add explicit defaults for S5-1…S5-4 in §4.5.
- Note in A-15's row that A-15 does not carry OM-20.

### COV-10 — Appendix A gives no Stage-B owner for recording the 24 deferred units and the 153 later-phase items

**What's wrong.**
- **T4 covers only part of the backlog.** It writes new DEFERRALS rows for counsel opinion, SEC-003 owner, second
  reviewer, ADR-124 allow and the MET-ENGINEERED D-rows, plus BL rows from BL-059 including the EVAL-004 revisit
  (l. 1360–1363).
- **Nothing records the rest.** No checklist item writes **LATER-01…22 and R11-ACQ-23a/b** (§15), or the 153
  `later-phase` universe items, into a committed register with their triggers.
- **Two are time-bound:**
  - LATER-21: CI runners before 24.04 end of support;
  - LATER-20: 90 days after P35.59.
- **Why it matters.** `AGENTS.md` gotcha 8 says *"A deferral not in that file did not happen."*

**Fix.**
- Add a T4 item: every LATER unit and every later-phase item becomes a DEFERRALS row (or a BL row) with its trigger and
  date; `check_backlog` / obligation checks verify the count (24 units; 153 items).
- Add `ADR_TRIGGERS.csv` cross-references for the 56 trigger-type later items.

---

## MINOR

### COV-11 — P36.72's acceptance claims more than its dependencies can deliver
§5.7 (l. 580) says P36.72 verifies that "every U-003 ask … has a working page passing its K-row acceptance", and §0
(l. 43) says 11C delivers "a working page for every U-003 ask". But P36.72's `depends_on` (`round11_plan.csv:186`)
excludes the 11D rows that deliver U-003.1 (P37.17–20), .2 (P37.21–28), .6 (P37.28–29), .7 (P37.30–34), .8 (P37.36–37),
.10 (P37.36, P37.41–42) and .11 (P37.32, P37.35, P37.62). **Fix:** scope P36.72 to the asks it can close (U-003.3, .4,
.5, .9 and first pages for the others), and name P37.63, P37.64 and P37.68 as the acceptance for the rest.

### COV-12 — Numbers that do not match the CSVs or each other
- **T2 runs.** "≈ 7.25" (l. 1324), but SEED-01…10 + SEED-16 = **7.75**.
- **Seed total.** "23.2" (l. 40, 1299), but the CSV says **23.25**.
- **S0/S1 wording.** §0 says "76 owner units plus their prerequisites" (l. 50). There are 58 owner rows; the closure,
  prerequisites included, is 76 rows / 78 runs.
- **S5 line count.** R-4 says "88 lines" (l. 1247); §0 says 87 (and 91 with S5-1…4).
- **§9.4's 101.** See COV-06.
- **U-003 receipt time.** §1.1 stamps it 21:28:52Z (feedback record); META_PLAN §7.1 says 21:29:45Z.
  Neither is flagged as a discrepancy.

**Fix:** correct the figures and record the timestamp discrepancy in Appendix B.

### COV-13 — Anomalies found by the mechanical recount
- **R11-MEM-10 is referenced twice:** by P34.33 and by P38.1 (`cat_ids = "NEW (S2; uses R11-MEM-10 contract)"`).
- **LATER-01 is the `cat_id` of four R10 marker rows** (HUMAN-H4, P32.22a, HUMAN-H5, P32.23) as well as of LATER-01.
- **12 chain rows are invisible to the checker.** P34.47, GATE-G4, P35.64, GATE-G5, P36.73, GATE-G6, P38.1–P38.4,
  GATE-ACCEPT-R11 and GATE-ANNOUNCE (6.0 runs) are "NEW (S2)" with no catalog entry. S1b's checker cannot see them
  until T4 switches rule (c), and §9.1 does not say that rule (a) has the same blind spot.

**Fix:**
- use a separate `uses`/`supersedes` column instead of `cat_ids` for references;
- add the 12 S2 units to the catalog, or make T4's switch cover rule (a) too.

### COV-14 — Small items with no Stage-B owner, or owned twice
- **No owner in T3/T4:**
  - validator V2 skipping superseded manifest rows (§8.6, l. 902);
  - the `git merge-base --is-ancestor origin/main <chainTip>` boundary check (§12, l. 1157), which is not in T5's
    OPERATING MODE list.
- **No owning artifact (no ADR, BL row or LATER unit):** Q-29's operator-accepted-risk revisit trigger (§3.4, §10.5).
- **No ADR in §7 although they change landed behaviour:**
  - B-14 (evidence retention: 365 days, unlocked);
  - B-3 (public source-id re-key with a restricted old→new map).
- **No status-line rule:** "amends / qualifies / extends" relations (ADR-099 §3, 081, 086/106, 124, 132, 134, 079/122)
  are not covered (l. 761–762).
- **Draft ids under two families in §6.2:** SIG-TRANSP-D26–D43 and SIG-CONF-D01/D05/D11. T1's de-duplication instruction
  covers only existing ids.

### COV-15 — Two owed-deferral dispositions overstate what Round 11 will close
- **D-P32.16-1 → "ticket → P37.59 (conditional)".** It needs a named moderation owner and a staffed reviewer rotation
  (DEFERRALS.md:641). Under the recommended B-8 (email-only until after the announcement) and U-008 (no humans besides
  the operator), it cannot close in Round 11.
- **D-P21.5-1 → P37.55 + OP-19.** Its closure depends on B-21 and B-6, whose defaults are "none" and "no deposit".

**Fix:** dispose D-P32.16-1 as `later-phase(trigger: GATE-ANNOUNCE passed and B-8 revisited)`, or annotate it "expected
to remain OPEN". Note D-P21.5-1's dependence on those defaults in §9.2.

### COV-16 — META_PLAN outcome 4 ("make the spec tell the truth") has no round-level success criterion
§13.2's six criteria omit META_PLAN §1 outcome 4. The A-4 default (spec unchanged; GOV ids stay PARTIAL/MISSING; F-31
stays open, §4.2 l. 283) disables it, yet it is not in §4.4. **Fix:** add a §13.2 criterion — 0 spec MUSTs contradicted
by a recorded operator decision without an ADR, waiver or owed row — and add the matching §4.4 row.

### COV-17 — The operator's chosen input mode is not reflected in the S5 plan
On 2026-09-30T16:27Z the operator said *"I want you to just interactively collect and log my answers to the
questionairre interactively in Claude one by one"* (META_PLAN §7.1). §11.2 plans S5 as one ≈ 45–50 min packet sitting
of 87 + 4 lines. **Fix:** state that S5 is collected one line at a time, with batch lines answerable in one reply, and
each answer logged verbatim with its `date -u` stamp. Otherwise ask the operator which mode to use.

---

## Closure checklist for `reviews/REVIEW_CLOSURE.md`

- **Before S5:** COV-01 and COV-02 (BLOCKER).
- **Before GATE-P:** COV-03 to COV-10 (MAJOR). Each needs a plan edit or an explicit, recorded rebuttal.
- **May ride T1–T4:** COV-11 to COV-17 (MINOR). Record each one's disposition.
