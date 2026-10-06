# Run ledger — SEED-12b (Stage B, T1 second bullet): §6.3 amendments and §6.5 waiver notes in their owning spec_src sections; Appendix G.7

- Harness: claude-code/claude-opus-5-5/subagent
- Skills: 8aeb6dc
- Started: 2026-10-01T07:55:55Z
- Closed: 2026-10-01T08:06:53Z
- Unit: SEED-12b — one of SEED-12's three contexts (`data/round11_plan.csv` SEED-12). This context owns the plan §6.3 amendments and §6.5 waiver notes in the **owning** `spec_src` section files and the new Appendix G.7 row set (`99c_appG_corrections.md`). Not owned here: the new §56 file and the §0.3 family table (SEED-12a), Appendix F rows and the ADR index (SEED-12c), `BUILD.sh` (orchestrator), the go-live spec, `AGENTS.md` gotchas.
- Worktree / branch: `/Users/stevenvitali/Eleutheria-next-phase`, `r11/seed` (no git state change made by this unit)
- Brief: `docs/build/planning/2026-09-30-next-phase/stageB/AGENT_BRIEF.md`; `stageB/CARRY.md`; plan Appendix A T1 bullet 2; plan §6.1, §6.3, §6.5, §7.

## What this unit did

Every change is an append: a dated note (or a superseding sentence) inserted after the requirement it amends, with the
requirement's own text left in place; the four §55 date corrections strike the recorded value through and add the true
time beside it (house pattern of Appendix G.1 C-01), never erasing it. Note dates come from `date -u` in the writing
command; operator times, words and sha256 prefixes are quoted from `PD/feedback/RATIFICATION_LOG.md` and the SEED-11 ADRs
(all twelve adopted-sentence hashes recomputed here from the log and equal to the ADRs'). No requirement id was minted,
no `**SIG-…-nnn (LEVEL)` definition pattern was written, and every id referenced resolves.

| file (`docs/research/_meta/spec_src/`) | ids / sections amended |
|---|---|
| `10_partI_charter.md` | SIG-CHART-025 amendment (A-17, Q-E2-22 a; ADR-172); SIG-CHART-033 outreach-status pointer (ADR-171) |
| `26_partII_s14_identity.md` | SIG-IDENT-028: census-driven demotion added for C0–C2 (ADR-153); holdout clause kept |
| `41_partIII_s16_schema.md` | SIG-STORE-011 waiver note (WV-11, ADR-189), after the trigger sketch; SIG-STORE-012 stated as standing |
| `42_partIII_s17_evidence.md` | SIG-EVID-009 (J3 NEW-2; ADR-162) |
| `51_partIV_s22_registry.md` | SIG-INGEST-029, SIG-INGEST-030a outreach-status pointers (ADR-171) |
| `52_partIV_s23to26_connectors_parse.md` | SIG-INGEST-035 waiver (WV-10, ADR-188); SIG-INGEST-046c note (not waived; ADR-168); §26 SIG-INGEST-036 rules 1/2/7 amendment + rule 6 waiver for DocumentCloud/MuckRock (WV-09, ADR-187; ADR-168, ADR-184); SIG-INGEST-037 counsel-clause waiver (WV-07, ADR-182) |
| `61_partV_s29to32_workflows.md` | SIG-RECON-058 (F-34; ADR-099/101/153); SIG-METRIC-007 (J3 D07; ADR-162) |
| `70_partVI_s33to36_research.md` | §35.1 outreach-timing status note covering SIG-CONTRIB-012/012a/013, SIG-CHART-033, SIG-INGEST-029/030a, SIG-GOV-024 (ADR-171; not amended in substance, not waived) |
| `80_partVII_s37to38_api.md` | SIG-EXPORT-012 (F-34; ADR-099/101) |
| `81_partVII_s39to41_ui.md` | SIG-UI-021/022 note (D-K0-6, non-weakening reading; ADR-158); SIG-UI-035 (J3 D23); SIG-UI-036 and SIG-UI-050 (A-12; ADR-155); SIG-UI-042 waiver (WV-04, ADR-179); SIG-UI-044 (D-K14-6, on-page reading) |
| `90_partVIII_s42to43_lic_pub.md` | SIG-LIC-004 (rights basis; ADR-167/169/183); §42.3 note (B-33 share-alike compartments only; ADR-169); SIG-LIC-009 waiver (WV-07, ADR-182); SIG-PUB-008 waiver note (WV-03, ADR-163) |
| `91_partVIII_s44to46_sec_gov.md` | SIG-SEC-003 (ADR-166); SIG-GOV-001/002 waiver (WV-05, ADR-180); SIG-GOV-003 SLA-time waiver + priority MET-DIFFERENTLY (WV-08, ADR-186); SIG-GOV-008 two-person waiver with scope + tombstone clauses restated as standing (WV-06, ADR-181); SIG-GOV-012/013 waiver (WV-01, ADR-165); SIG-GOV-015 waiver (WV-02, ADR-164); SIG-GOV-024 outreach pointer |
| `95_partIX_s47to50_eng.md` | SIG-ENG-039 (DRAFT-ENG-4; F-32) — additions only |
| `96_partX_s51to54_plan.md` | SIG-ENG-031 (DRAFT-ENG-5; "CI green" = SIG-MEM-007) — additions only |
| `96b_partXI_s55_six_streams.md` | §55.1 island-clause note (ADR-155); SIG-EVAL-004 waiver note (A-6, ADR-153); SIG-EVAL-005/006/007 owner re-homing; §55.9 Round-11 disposition (T-EVAL-IND; ADR-152); **four date corrections** (S3 deferral 2026-09-28T01:15:49Z; GATE-G3 2026-09-28T03:49:14Z; ADR-146), recorded value struck through |
| `99c_appG_corrections.md` | **new G.7**: G.7.1 Part XII row (R11-X1, carry item from SEED-12a); G.7.2 twelve waiver rows R11-W1…W12; G.7.3 amendment rows R11-A1…A17; G.7.4 date-correction row R11-C1 (§55 true dates; R10-A6, App F rows and landed ADR bodies not edited; sqitch L44–52 never re-stamped); G.7.5 checked-and-not-amended table |

Wrong id fixed: the plan's "SIG-CONTRIB-030a" is written as SIG-INGEST-030a everywhere (G.7 R11-A15 records the correction
without writing the non-existent id), and SIG-INGEST-029 is included.

Not touched (other owners): `96c_partXII_s56_round11.md` and the §0.3 family table (SEED-12a; no new prefix opened here),
`99a_appF_adr.md` (SEED-12c), `00_front_part0.md`, `docs/2_canonical_design_spec.md`, `BUILD.sh`, the go-live spec, any ADR,
`AGENTS.md`.

## MUST-weakening test (plan §6.5; carry item SEED-11b)

| draft | verdict | action |
|---|---|---|
| SIG-UI-021/022 (D-K0-6, K0 §7 text "aggregated overview graphs … MAY serve as the global entry point") | the "global entry point" clause **weakens** SIG-UI-022's default ego view; the ratified statement itself ("the global graph is a set of aggregated overviews, not a raw national node-link graph") does not | wrote only the non-weakening reading (overviews as alternative views; both MUSTs unchanged incl. the ego default); the entry-point clause is listed in G.7.5 as needing the operator's words |
| §42.3 / SIG-LIC-006 "physical ODbL table → export-boundary compartments" (RISK-P4-07) | **weakens** (drops the stored-table clause); no operator decision | not applied; only B-33's share-alike compartments written; listed in G.7.5 |
| SIG-INGEST-004 binding-level versions (F2a NEW-7, ADR-121) | **weakens** ("logical identity MUST include extractor_version …") | not applied; listed in G.7.5 |
| SIG-ENG-004 "MET = criteria 1+2" (F2a) | **weakens** the all-five DoD | not applied; listed in G.7.5 |
| SIG-ONTO-060 scope list | widening a closed list relaxes it; needs the realised enum | not applied; recorded in G.7.5 |
| SIG-EXPORT-002 RO-Crate clause (J3) | no decision recorded | unchanged; G.7.5 |
| SIG-UI-036/050 (A-12) | relaxes "every other public page MUST ship zero client JavaScript" for T1 pages | **written** — the operator chose it at A-12 against "Keep three islands", through the new-ADR change path SIG-UI-050 names (ADR-155); the note says it is a relaxation. ADR-155 is not a WAIVED ADR — T4's checker may need to classify it |
| SIG-CHART-025 (A-17) | plan §5.10 / TS-05 class it non-weakening; the operator answered Q-E2-22 = a to amend it | written |
| SIG-UI-044 (D-K14-6, B-22 batch) | weakening only if "one action away" means another page | written in the on-page reading (labelled); a link-away form would need the operator's words |
| SIG-IDENT-028 (ADR-153 D4 "census-driven demotion *replaces* holdout-driven demotion") | replacing would remove the holdout-demotion clause for C0–C2, which A-6's sentence (EVAL-004 only) does not name | written as an **addition** (census demotion added; holdout clause not waived) |
| outreach timing (ADR-171 "changes from a pre-connector precondition to an owed later-phase obligation") | re-timing would weaken SIG-CHART-033/SIG-INGEST-029/SIG-CONTRIB-012 | written as an owed-status note: requirements unchanged, not waived; a connector written before outreach leaves the precondition **unmet and owed** (GATE-ANNOUNCE list) |
| every other §6.3 row | additive or a waiver with the operator's adopted sentence | written |

## Checks run

| check | result |
|---|---|
| `python3 docs/build/tools/check_spec_src.py` | **FAIL, 2 problems, neither from this unit:** (1) BUILD.sh reproduction not byte-identical — expected, `BUILD.sh` is the orchestrator's and was not run; (2) ADR-146…189 absent from Appendix F — SEED-12c's rows. (The tool compares against the committed built spec, so its id count still reads the pre-§56 spec.) |
| in-memory assembly with the tool's own `assembled()` + `DEF_RE`/`REF_RE` (spec file not written) | **777 unique definitions (715 + SEED-12a's 62), 0 duplicates, 0 dangling references** — the notes add no definition and every id they cite is defined |
| wrapped-line marker scan over every added line | no continuation line begins with a list, heading, quote or table marker (only the intended G.7 headings) |
| word-diff of `spec_src` | the only replaced tokens are the four `2026-10-19` values, now kept as `~~2026-10-19~~` beside the true time |
| plan-row ids cited (P34.17, P34.45, P35.38a, P36.1a, P37.7, P37.8, P37.44, P37.45, P37.71, P37.72, LATER-01/02/04) | all exist in `data/round11_plan.csv` |
| adopted-sentence sha256 (A-6, WV-01…WV-11) recomputed from the log | all equal the ADRs' values |
| `bash scripts/docs/check-build-memory.sh .` (structural, read-only) | exit 1: **1 violation** — `docs/adr/README.md` stale vs a fresh adr-index regeneration (SEED-11's new ADRs; the index regeneration is a T1 orchestrator item); 74 legacy warnings; nothing flagged in this unit's files (this ledger carries its `Harness:` line) |

## Open issues for the orchestrator / other units

1. **Operator waivers needed (not written):** SIG-UI-022 default view replaced by an overview (K2's `/network/` → `/explore/?v=2&overview=access` redirect makes an overview the old explorer's landing view — either keep an ego default or put a waiver to the operator); SIG-LIC-006 stored-table clause (ADR-027's appended trigger evaluation by SEED-11d says "T1 amends §42.3 from a physical ODbL table to export-boundary compartments" — that amendment was **not** made; reconcile the evaluation text or obtain a waiver); SIG-INGEST-004 (P35.34 is titled "INGEST-004 binding-version test" — it either adds versions to the digest or needs a waiver); SIG-ENG-004.
2. **ADR/spec consistency to review:** ADR-153 Decision 4 ("replaces") vs the additive SIG-IDENT-028 note; ADR-171 Decision 1 ("changes from a pre-connector precondition") vs the owed-status note — P36.77 writes a DocumentCloud/MuckRock connector (both in the §6 table) before outreach, so SIG-CHART-033/SIG-INGEST-029/SIG-CONTRIB-012 are unmet-and-owed for it (WV-09 waived crawler rule 6 only).
3. **T4 (SEED-14):** classify ADR-155's SIG-UI-050 relaxation under the "weakens a MUST" checker rule; record the split verdicts named in the notes (GOV-003, INGEST-035, STORE-011, GOV-008, UI-042, LIC-009/INGEST-037 `accepted_scope`).
4. **SEED-12c:** Appendix F rows for ADR-146…189 and ADR-072; `check_spec_src.py` `FOLD_BACK_IDS` (+62, SEED-12a's list); spec version line; the go-live spec (HG-03 text for SIG-LIC-004, GL-GATE-07/08 re-confirmed — plan §6.3 "SIG-LIC-004/009 + HG-03 text" is go-live-spec text, not `spec_src`); SIG-ONTO-060's realised scope list needs an owner.
5. **Orchestrator:** run `BUILD.sh` and re-run `check_spec_src.py`; `AGENTS.md` gotcha 6 / `web/AGENTS.md` gotcha 1 (K0 §7.1–7.2) are another T1 item, not done here.
