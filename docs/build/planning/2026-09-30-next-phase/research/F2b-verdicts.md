# F2b — Requirement verdicts: gated and reduced-scope half, plus the verdict vocabulary

**Row F2b** of META_PLAN §6 F. The orchestrator split F2 into two halves for context size; F2a is
the engineering and stale-routing half. **Written 2026-09-30T17:10–17:25Z** (`date -u`) at worktree
HEAD `c28756d9` (`claude/next-phase-planning`), reading the control files as committed. The row is
read-only: the only files it writes are this note, `data/coverage_delta_F2b.csv` and
`findings/incoming/F2b.csv`. `COVERAGE_MATRIX.csv` is not edited; per P10, T4 applies the verdicts.
Live GETs made: 5 (`/corrections/`, `/editorial-standards/`, `/methodology/`, the Software Heritage
origin API, and a zenodo.org record search), all read-only.

**Evidence classes (P1).** `code` = file:line read in this row. `live-read` = a GET or `gh` read made
in this row. `recorded-execution` = a dated run recorded in the repo. `inference` = labelled where
used. The MET-DIFFERENTLY sample was first audited by a read-only Explore subagent. This row then
re-read every file:line it cites in the delta CSV (29 spot checks, all confirmed) before using any
of it.

**Scope (55 ids).**
- (1) The 20 human- or operator-gated not-MET ids (Appendix C).
- (2) The 8 MET ids met only on reduced scope.
- (3) The 9 MET ids that cite an owed deferral (A3 NEW-1).
- (4) SIG-PUB-008 and SIG-UI-042.
- (5) A stratified random sample of 13 of the 75 boilerplate MET-DIFFERENTLY rows (seed `20260930`;
  quotas CHART 4, EPIS 3, ENG 3, PUB 2, ONTO 1), plus both `deviated(ADR)` rows, plus one purposive
  addition (SIG-CHART-033, a cross-check against SIG-CONTRIB-012).

---

## 1. Headline

| current → proposed | n | ids |
|---|---|---|
| MET → **MET-ENGINEERED** | 12 | TRUST-004, 007, 008, 009, 010; FIND-006, 007; DOS-002, 003, 004, 005; ACQ-004 |
| MET → **AT-RISK-INTEGRATION** | 3 | EVAL-003, EVAL-004, PUB-008 |
| MET → **PARTIAL** | 2 | MEM-002, UI-042 |
| MET → MET (stays) | 2 | MEM-003, MEM-004 (the owed deferral they cite is not a leg of their text) |
| MET-DIFFERENTLY → MET | 7 | EPIS-012, EPIS-022, PUB-014, PUB-014b, ONTO-005, UI-038, UI-047 |
| MET-DIFFERENTLY → PARTIAL | 6 | CHART-017, CHART-019, CHART-034, EPIS-009, ENG-002, ENG-005 |
| MET-DIFFERENTLY → AT-RISK-INTEGRATION | 1 | ENG-024 |
| MET-DIFFERENTLY → **WAIVED(ADR)** | 1 | CHART-033 |
| MET-DIFFERENTLY → MET-DIFFERENTLY(RISK) | 1 | CHART-025 |
| PARTIAL → MET | 2 | GOV-021, GOV-023 |
| PARTIAL → MET-ENGINEERED | 2 | GOV-022, EVID-019 |
| PARTIAL → MISSING | 2 | GOV-013, GOV-015 |
| PARTIAL → WAIVED(ADR) | 2 | CONTRIB-013, GOV-024 |
| PARTIAL → PARTIAL (reason re-stated) | 6 | GOV-012, GOV-016, UI-001, LIC-012, EVAL-001, EVAL-002 |
| MISSING → WAIVED(ADR) | 2 | CONTRIB-012, CONTRIB-012a |
| MISSING → MISSING | 4 | SEC-003, EVAL-005, EVAL-006, EVAL-007 |

**Totals over the 55 ids.** Current: MET 19 · MET-DIFFERENTLY 16 · PARTIAL 14 · MISSING 6.
Proposed: MET 11 · MET-DIFFERENTLY 1 · **MET-ENGINEERED 14** · PARTIAL 14 · MISSING 6 ·
AT-RISK-INTEGRATION 4 · **WAIVED(ADR) 5**.

- Of the 19 MET rows, only 2 survive as MET.
- The 5 WAIVED verdicts all depend on one **operator decision**: ratify a Stage-0 outreach waiver
  ADR. If the operator declines, CONTRIB-012/012a, GOV-024 and CHART-033 become MISSING and
  CONTRIB-013 becomes PARTIAL.
- The 14 MET-ENGINEERED verdicts require T4 to open the missing D-rows first (§2.4; finding NEW-6).
  Only GOV-022 and EVID-019 lack one.

---

## 2. The verdict vocabulary (proposal for S5; applied in T4)

### 2.1 The one question a verdict answers

> *Does the landed and operated system satisfy the requirement text as written, at the evidence
> domain the text demands, with no human or live leg still owed?*

Five things that used to be collapsed into the verdict are kept separate:

- **The evidence domain achieved.** The landed `coverage-assessment/1` ladder is `fixture <
  implementation < composed-db < hosted < public` (`docs/build/tools/obligation_events.py:80`). It
  maps onto P5 as: fixture-verified, engineered, staging-verified, live-executed, public.
- **The human leg**, which is orthogonal to the ladder (P5 `human-completed`).
- **Operator acceptances.** Scoped signatures authorize an action. They never satisfy criteria.
- **The home** of anything still owed: a D-row, BL row, manifest row or ADR.
- **The routing.**

Today these collapse: "Closed P32.25 … NO production serve" is recorded as `MET`, and the capstone
headline "34 MET" (CAPSTONE_CLOSURE §(f1)) counts fixture-verified machinery as requirement
satisfaction. That is the F-16 / E1 NEW-8 / A3 NEW-1 failure.

### 2.2 Definitions, entry and exit

| verdict | definition | entry (all required) | exit |
|---|---|---|---|
| **MET** | Every clause of the text is satisfied at its required domain. | Evidence cited per clause (test, recorded execution, live read, or the document itself for documentation-only requirements). `achieved_domain ≥ required_domain`. No OPEN or PARTIAL D-row is a leg of this requirement. No operated or public surface contradicts it. | **Demote** on a contradicting live read, a regressed test, a newly found owed leg, or a vanished evidence path. |
| **MET-DIFFERENTLY(ADR-nnn \| RISK-id)** | The intent is satisfied by a mechanism other than the one the text names. | An accepted ADR that names the id, the alternative and why it is sound, with the alternative itself evidenced. **Or**, only for a requirement that cannot be verified automatically, the SIG-ENG-005 route: a risk-register row naming the compensating control. A prefix default, a bulk signature or boilerplate is never enough. | If the spec is later amended so the alternative *is* the text (UI-038), promote to **MET**. If the ADR is superseded, re-verdict. |
| **MET-ENGINEERED(D-id…)** *(new)* | All engineering the text requires is built and verified at ≥ `implementation`. What remains is only live-execution, operator or human acts. | The owed acts are named in ≥1 **OPEN/PARTIAL DEFERRALS row** (a BL row alone is not enough: BACKLOG is future work, DEFERRALS is owed obligation). The shipped engineering can perform the leg **without new code**. **No surface claims the leg happened.** Artifacts disclose the owed leg. | **Up to MET** when every cited D-row is DONE with evidence at the required domain. **Down to PARTIAL** if a surface claims the leg happened, or the D-row is WONTFIX'd with no ADR. **Down to AT-RISK-INTEGRATION or PARTIAL** if the leg turns out to need code. **To WAIVED** only through an ADR. |
| **PARTIAL** | Some clauses are satisfied and others are unbuilt; or a public surface or record contradicts the requirement. | Exactly one live home (a manifest row ≥ 201, an open BL row, or an OPEN D-row). | To MET / MET-ENGINEERED when the missing clauses land. |
| **MISSING** | No conforming implementation exists. | Exactly one live home. | As for PARTIAL. |
| **AT-RISK-INTEGRATION** | A conforming component exists and is tested, but the operated or public path does not use it, or still runs a non-conforming path. | Home = an integration ticket. If activation also needs a human act, cite the D-row too. | To MET or MET-ENGINEERED once the operated path uses the component. |
| **WAIVED(ADR-nnn)** *(new)* | The operator has explicitly decided the requirement, or a named clause of it, will not be satisfied for a stated scope or period. | An accepted ADR naming the id, the operator's words verbatim, the risk accepted, compensating controls and a revisit trigger. A spec_src waiver note pointing to the ADR. No public surface claims the waived property. **A WONTFIX D-row or a skipped gate on its own is not a waiver.** | When the revisit trigger fires, re-verdict. If the operator reverses the decision, the row returns to PARTIAL or MISSING with a home. |
| **N/A-RATIONALE** | A rationale statement with no build obligation. | Unchanged (7 rows). | — |

**Recommended new matrix columns** (additive, so the matrix stays back-compatible):

- `required_domain` — one of fixture, implementation, composed-db, hosted, public, plus a `+human`
  flag.
- `achieved_domain`.
- `owed_legs` — D-ids.
- `accepted_scope` — see §2.5.

T4 writes every verdict change as a `coverage-assessment/1` event carrying its `domain`. This closes
the SIG-MEM-002 gap below: requirement assessments derived from transitions go from 4 of 715 to all
715. The matrix verdict then becomes the projection of the event heads, so the event layer and the
CSV can never disagree.

### 2.3 How each verdict maps to DEFERRALS and BACKLOG

| verdict | DEFERRALS | BACKLOG |
|---|---|---|
| MET | No OPEN or PARTIAL row may name the id as a leg. Rows cited only for context are listed in the note, not in `owed_legs`. | Enhancements only. |
| MET-DIFFERENTLY | None required. | The ADR's revisit trigger has its BL home (current practice: BL-002/056/057/058). |
| MET-ENGINEERED | ≥1 OPEN/PARTIAL row in `owed_legs`. Each such row names the SIG id in its cell, so the link is bidirectional (A3's universe links check it). | Optional. |
| PARTIAL / MISSING / AT-RISK-INTEGRATION | Allowed as the home. | Allowed as the home. Routing to a **landed** ticket is an error (F-30). |
| WAIVED | Any prior row is WONTFIX citing the ADR. | One BL row for the revisit trigger. |

### 2.4 `check_coverage_matrix.py` and the capstone

The validator runs in no gate and checks only structure (finding **NEW-4**). Proposed changes for T4
and B4:

1. **Wire it in.** Add it to `make docs-check` and CI, and pass its path in `make check`.
2. **Verdict grammar.** Extend the enum with `MET-ENGINEERED` and `WAIVED`, and parse the
   parameters:
   - `MET-DIFFERENTLY` must name an ADR file that exists and mentions the id, or a RISK row that
     exists and names the id.
   - `WAIVED` must name an accepted ADR that contains the id and a `## Revisit trigger`.
   - `MET-ENGINEERED` must have non-empty `owed_legs`.
3. **Cross-checks against the obligation register.** These use `events.jsonl` heads, the same
   parser A3 used.
   - A MET row citing an OPEN/PARTIAL D-id in any column is an error (the 17 A3 NEW-1 rows fail
     today).
   - A MET-ENGINEERED row whose D-rows are all DONE is an error (stale: promote after verifying).
   - A MET-ENGINEERED row citing a WONTFIX D-row with no WAIVED ADR is an error.
   - A WAIVED row whose D-row is still OPEN is an error.
4. **Routing liveness.** Routing to a ticket that has a BUILD_INDEX row is an error.
5. **Evidence liveness.** Every cited path must exist (the UI-038 row cites a deleted file).
6. **Domain.** A MET row with `achieved_domain < required_domain` is an error. Reuse the landed
   `coverage/domain-override` rule (`obligation_events.py:1066-1080`) against the matrix.

**Capstone.**

- Report every verdict separately. Never add MET-ENGINEERED into MET in a headline (P5).
- Use two sums:
  - *engineering closed* = MET + MET-DIFFERENTLY + MET-ENGINEERED;
  - *requirement satisfied* = MET + MET-DIFFERENTLY only.
- List WAIVED rows with their ADRs.
- Join check: every D-id in a MET-ENGINEERED `owed_legs` cell appears in the capstone's OPEN
  register (today §(f5)).
- A phase gate (SIG-ENG-002) may pass with MET-ENGINEERED rows only if each D-row has owner,
  landing and closure condition.
- A publication gate must list the MET-ENGINEERED rows it scopes out (`accepted_scope`).
- No public page may present a MET-ENGINEERED or WAIVED property as achieved.

This does not overturn ACCEPT-R10. That readout accepted "the honest scope state … production
exposure OPEN … the S3 spine deferred … intake non-operational" and "the round's engineering is
closed against its amended plan". That is precisely the MET-ENGINEERED meaning. The "34 MET" count
was the only part that overstated it.

### 2.5 Recording reduced-scope operator acceptances (GATE-G3 and similar)

A scoped signature is an **authorization to act**, not a verdict. Recording rules:

1. **New column `accepted_scope`**, in the form `<readout>@<date>#<clause>`, for example
   `GATE-G3@<as-signed date, see F-21>#scope-3,intake,eval`. It is set on each requirement whose
   criteria the signature scoped out: TRUST-009, TRUST-010, FIND-006, DOS-002…005 and FIND-007.
2. **A scoped acceptance never raises a verdict.** Every clause it scoped out must be an OPEN
   D-row: D-R10-PUBLISH-1 (production half), D-P32.16-1, D-R10-HUMAN-1, D-P32.23a-1. The verdict
   is at most MET-ENGINEERED.
3. **The spec keeps the clause.** ADR-145 already added exactly this clause to SIG-TRUST-009
   (spec:7377): "disclosed, not satisfied … the full criterion set remains the bar". This proposal
   makes the matrix agree with the spec it already amended.
4. **The readout's signing date is not a clock.** GATE-G3 reads "2026-10-19", which is after the
   commit date (F-21). T4 must cite the commit-derived date B1 assigns.
5. **Converting a scoped acceptance into a waiver.** The operator records a WAIVED(ADR) for the
   scoped-out clause, with a revisit trigger. The readout alone never does it.

### 2.6 Worked examples

**(a) SIG-TRUST-009: MET → MET-ENGINEERED; `accepted_scope` = GATE-G3.**
- *Text:* a new public release requires "… tested intake operating ownership … unauthenticated
  verification … tested prior-release rollback. A planning artifact, successful build or agent
  judgment cannot sign this gate." ADR-145 then appended (spec:7377): the GATE-G3 scope was
  "disclosed, not satisfied".
- *Achieved:* `composed-db`/`fixture`. `runs/P32.25.md:11-12` records `live_verification=false`,
  "bounded/staging namespace only; NO production serve". The candidate holds 0 records (F-15), and
  no Round-10 surface is deployed (F-14).
- *Required:* `public`.
- *Owed legs:* D-R10-PUBLISH-1 (production half), D-P32.23a-1, D-R10-LIVE-1, D-P32.16-1.
- *Entry check:* the machinery exists and was verified in staging; no surface claims production
  exposure; the D-rows are OPEN. **Pass.**
- *Exit:* MET once P32.25 re-runs against the production candidate with unauthenticated public GETs.

**(b) SIG-CONTRIB-012: MISSING → WAIVED(ADR).**
- *Text:* contact must be attempted and recorded before any ecosystem connector is written.
- *Fact:* no outreach ever happened (`STAGE0_OUTREACH_RECORD.md:7`;
  `tests/connectors/test_stage0_outreach.py:54` asserts none). The operator skipped it on 2026-09-16
  (D-P21.1-2 WONTFIX). Connectors for atlas, osm, flock_portal and records were written anyway.
- The matrix records one obligation three ways (E1 NEW-8): CONTRIB-012 MISSING, CHART-033
  MET-DIFFERENTLY, INGEST-029 MET.
- *Entry check for WAIVED:* needs a new ADR with the operator's words, the accepted risk (upstream
  goodwill; RISK-P0-17 single point of failure) and a revisit trigger (e.g. "a compact project
  objects, or D-JURIS.2-1's HG-04 outreach becomes feasible"), plus a spec_src waiver note on
  CONTRIB-012/012a/013, GOV-024 and CHART-033. **Until the ADR lands, MISSING stands.** WONTFIX
  alone is not a waiver.
- *Operator decision (S5):* waive the rule, or keep it owed with a plan.

**(c) SIG-UI-042: MET → PARTIAL (MET-ENGINEERED is blocked by a public claim).**
- *Engineered:* `assertReviewReleasable` blocks release on an undispositioned finding
  (`web/tests/unit/editorial.test.ts:77`).
- *Owed:* two humans reviewing a real rendered dossier.
- *Blocked:* the live `/editorial-standards/` (GET 2026-09-30) renders "Reviewers Reviewer A
  (counsel stance); Reviewer B (counsel stance) Review date 2026-08-19 Release status Releasable".
  That is a fixture constant (`corrections-methodology-fixture.ts:189-215`) dated before the
  repository existed (E1 NEW-1 S0; E3 NEW-1). It is a public claim that the owed leg happened, so
  the MET-ENGINEERED entry rule fails.
- *No D-row exists* for the review (NEW-6).
- *Path:* withdraw the fixture claim, open a D-row, and the verdict becomes MET-ENGINEERED(new
  D-id). It becomes MET after a real signed review.

---

## 3. Per-id notes

The full evidence, D-ids and dispositions for each id are in `data/coverage_delta_F2b.csv`. This
section gives the reasoning.

### 3.1 The 20 human- or operator-gated not-MET ids

**Stage-0 outreach group: CONTRIB-012, 012a, 013, GOV-024 (and CHART-033 in §4).** One act was
skipped by the operator (D-P21.1-2 WONTFIX 2026-09-16), so one waiver ADR decides all five rows.

- CONTRIB-013's *content* rule is already met by `stage0-outreach-letter.md:52`, which includes the
  archival-succession offer. It becomes operative only if an offer is sent.
- GOV-024's matrix note wrongly equates "offer archival insurance" with the P21.5 mirror
  infrastructure. The obligation is an act, the same act as outreach.

**Legal home and governance: GOV-012 PARTIAL, GOV-013 → MISSING, GOV-015 → MISSING, GOV-016
PARTIAL.** E1 (E1-03, NEW-7, NEW-11) establishes the facts: an individual legal home described as
"interim"; a board that is asserted to exist but does not; and "not a public launch" text left in
place after go-public. F2b adds:

- GOV-013 has **nothing** identified. `contributor-safety.md:55-57` nonetheless tells contributors
  such resources and a "named, monitored contact path" exist (**NEW-5**). PARTIAL overstated it.
- GOV-015: the board's non-existence is the fact, so MISSING. A WAIVED verdict would need the
  operator to accept, explicitly, the risk the spec names: editorial calls made "by whoever happens
  to hold commit access".
- GOV-016 is a documentation requirement. The funding-exclusion policy is real. The
  separation-of-powers bullet depends on the fictional board, so the row becomes MET as soon as the
  doc states the true posture.
- None of GOV-012/013/015 has an owed row (NEW-6).

**Continuity: GOV-021 → MET, GOV-022 → MET-ENGINEERED, GOV-023 → MET, EVID-019 → MET-ENGINEERED.**
The pre-Round-10 notes are stale.
- GOV-021's three clauses (tested, decay path documented, keepalive designed in) are evidenced. The
  keepalive has **0 runs**; the first is scheduled for 2026-10-01T07:00Z (**NEW-7**, a G-stream
  observation).
- GOV-023's commitment is published in the now-public repo. OCFL readability without SIG code is
  tested (`tests/e2e/test_composed_stack.py:189`, `tests/evidence/test_digest.py:58`).
- GOV-022 and EVID-019: the engineering exists (deposit client, push client, torrent, `swh-save`).
  The remaining acts are operator or live:
  - SWH save-now. Its only blocker, the repo being private, is gone: `gh repo view` → PUBLIC.
    Live: the SWH origin API returns 404 (E1 NEW-14).
  - The production Zenodo deposit per quarterly release. It has **no D-row**, only BL-029; the
    D-P21.5-1 residue omits it. DEPOSITS.md holds only sandbox or dry-run rows, and live
    zenodo.org has 0 records (NEW-6).
  - A non-GCS geographic mirror. `endpoint_url=""`, and the only region is US-CENTRAL1 (G1 NEW-4).

**SEC-003 MISSING (stays).** The `/corrections/` "Transparency report" (live: `legal_demand: 0`,
`refused: 0`) is the SIG-GOV-011 corrections log. It is not a legal-demand report, and no
demand-response posture is documented anywhere. The routing `P20.1:backlog` points at no BL row
(E1 NEW-5). This is agent-draftable and operator-adoptable, so it need not wait.

**UI-001 PARTIAL (stays; reason re-stated).**
- The row is routed to landed P21.7, and its human study (D-P21.7-2) was WONTFIX'd.
- The live human leg is D-R10-USERS-1.
- It is not MET-ENGINEERED: no artifact traces surfaces to the persona table (the P32.24 tasks
  T1–T7 are not keyed to personas), and E3 NEW-5 shows no protocol can test the live site for the
  design-center persona. C2/C3 produce the design evidence.

**LIC-012 PARTIAL (stays; the blocker is now engineering, not human).**
- Met: open code and open schemas (the repo is PUBLIC), versioned snapshots, the API.
- Unmet: downloads are unreachable (J1 NEW-1), provenance is synthetic (J1 NEW-4/8), and there is
  no data dictionary (J1 NEW-11). Stream J owns all three.
- Appendix C's "human-gated" label is stale.

**EVAL-001/002 PARTIAL (stays).** The P32.9 campaign machinery conforms and would be MET-ENGINEERED
(D-R10-HUMAN-1), but `/methodology/` publicly presents the non-preregistered P28.1 holdout as "the
frozen, human-verified holdout". Its gold verifier and adjudicator are an agent and rule code
(E1 NEW-10, F-06). That is a surface claiming the human leg, so the entry rule fails. EVAL-002 may
also need reviewer-access engineering (E3 NEW-2).

**EVAL-005/007 MISSING (stay).** Correctly recorded against the deferred spine. F4 decides
re-entry.

**EVAL-006 MISSING (stays).** It is **violated today**: the current `/methodology/` claims do not
name populations, source mix or time window. That labelling fix is engineering-only and should not
wait for the spine (**NEW-3**).

### 3.2 The 8 reduced-scope MET ids → all MET-ENGINEERED

In every case the requirement text demands a live or human leg that is owed, and the engineering is
fixture- or staging-verified.

- **TRUST-009:** worked example (a).
- **TRUST-010:** "After the final evaluation decision …". No decision exists, and ADR-145's own
  clause (spec:7381) says "A deferred-evaluation candidate cannot satisfy release acceptance".
- **FIND-006:** the receiver is built and refuses to operate by design (`operational=false`); live
  `/intake/` returns 404.
- **DOS-002:** the completion validator is built; no dossier is complete.
- **DOS-003/004/005:** the content rules are implemented over hand-authored stand-in documents
  (`SOURCES.md`), with the live return passes `prepared_not_executed`. DOS-005's Part VIII
  preflight clause is genuinely met now. E4 NEW-7: the live-pass target URLs diverge from the
  research record.
- **ACQ-004:** "actual … funnel" versus `captured_live=0`, and "measured gap closure" versus
  "descriptive recommendations (no matched comparison run)".

### 3.3 The 9 A3 NEW-1 rows: 5 reduced-scope, 2 contradicted, 2 legitimately MET

- **Reduced scope → MET-ENGINEERED:**
  - TRUST-004 (D-P32.3-1: legacy keys not re-keyed; hosted count never measured, E3 NEW-7);
  - TRUST-007 and TRUST-008 (D-R10-LIVE-1: no hosted audit, no production recovery);
  - FIND-007 (D-R10-USERS-1, plus the portfolio ran on a 0-record candidate and a synthetic 75-record
    corpus, F-15).
- **Contradicted by the operated path → AT-RISK-INTEGRATION:** EVAL-003 and EVAL-004 (**NEW-3**).
  - Production auto-write for tiers 1g and 3g is decided by a point-estimate holdout precision over
    an agent-verified gold set (`camera_site_rules.toml:40-47`).
  - The public report gives P/R/F1 1.000 with no n, weights or interval.
  - The conforming `eval-confidence/1` stays `mode="shadow"`.
  - D-R6.1-EVAL's PROVISIONAL disclosure is a compensating control, not satisfaction.
  - Engineering fix, no humans needed: route eligibility through the lower bound (with zero labels,
    every tier demotes to review-only). If the operator prefers to keep provisional auto-writes,
    that is a **WAIVED(ADR)** decision.
- **MEM-002 → PARTIAL.** The obligation side is complete (97 events). The requirement side is not:
  `coverage_assessments.jsonl` covers 4 of 715 ids, and the other 711 current verdicts fall back to
  the matrix (A3 README). Shadow mode itself conforms. T4 closes the gap by writing the F2 deltas as
  assessment events (§2.2).
- **Legitimately MET:**
  - MEM-003: the text itself says "workflow activation stays shadow-only until a verified
    operator-approved cutover". D-R10-MEMORY-1 is a separate operator obligation, not a leg.
  - MEM-004: its note cites D-R10-MEMORY-1 as context only.

### 3.4 SIG-PUB-008 and SIG-UI-042

**PUB-008: MET → AT-RISK-INTEGRATION, not WAIVED.**
- The requirement is scoped to officer naming (§43.4). The Python gate is fail-closed: fewer than
  two independent written reviewers means no-publish (`policy/src/policy/officer.py:82-90`).
- The sole-maintainer waiver (D-P21.4-2; ADR-145:118-122) applies to HG-11 go-public. The waiver's
  own text says "officer-naming stays default-no-publish", so it is **not** a waiver of PUB-008.
- The web publication gate publishes US public-employee names on jurisdiction alone, with no
  PUB-007/008 routing (`web/src/lib/publication.ts:36-71`; the OKC fixture's police-chief row;
  E1 NEW-12). It is latent today (`/dossier/okc/` → 404).
- ADR-145's premise that "the published surface makes no two-reviewer claim" is false because of
  `/editorial-standards/` (E1 NEW-1).

**UI-042: MET → PARTIAL.** Worked example (c).

---

## 4. The MET-DIFFERENTLY sample: sound or inflated?

**Where the family comes from.** It is a classifier default, not a set of reviewed deviations.
`docs/build/tools/classify.py:229-230` assigns `MET-DIFFERENTLY` / `accepted` / the boilerplate note
to **any id with no evidence anywhere** (no code, tests, ADRs, PR bodies, traceability or risk
register) **whose prefix is CHART, ENG, EPIS, SEC or PUB**. The same "no evidence" state under any
other prefix returns MISSING (`:232`). That default produced 65 of the 75 rows; 10 are hand
overrides (`:76,98,102,106,110,152`). The operator bulk-accepted all 75 at HG-14 (2026-09-08, 0
rejected; CAPSTONE_CLOSURE §(e)). That signature row was later deleted from the LEDGER (F-22), and
no row cites an ADR or a test.

**Sample result** (13 random boilerplate rows, each re-read):

| outcome | n | ids |
|---|---|---|
| actually MET, just uncited | 5 | EPIS-012, EPIS-022, PUB-014 (vacuous: no RF data reaches the UI; add a lint guard), PUB-014b, ONTO-005 |
| sound alternative, but needs its SIG-ENG-005 risk row | 1 | CHART-025 ("narrowly excellent" cannot be measured automatically) |
| **not met** | **7** | CHART-017 (the immutable-capture clause: legacy captures possibly lost per ADR-125:10-12; hosted bucket overwritable per G1 NEW-4); CHART-019 (map and search counts lack denominators; F-05); CHART-034 (1 of 6 leverage measures exists and reads 0 of 0; **NEW-8**); EPIS-009 (derivation guard inert; **NEW-2**); ENG-002 and ENG-005 (the build reports partial work as done, and this family *is* the ENG-005 anti-pattern); ENG-024 (public exports on a metered public-read GCS bucket; the R2 path is unconfigured; J1 NEW-12) |

The purposive CHART-033 row is contradicted outright: outreach was skipped, not met differently.

**Conclusion: the family is inflated.** Seven of thirteen (≈54%; Wilson 95% CI ≈ 29–77%) are not
met. By inference, roughly **19–50 of the 65 prefix-default rows** are not met, and most of the rest
are MET but lack citations. The family does not meet the bar its own name implies. T4 should
re-verdict all 75 row by row (≈75 fresh reads; F2a or a T4 sub-row), sorting each into MET-with-
citation, MET-DIFFERENTLY with an ADR or ENG-005 risk row, or PARTIAL/MISSING with a home. **Do not
bulk-carry the HG-14 acceptance forward.** A signature over a boilerplate note is not evidence
(P1, P4).

**The two `deviated(ADR)` rows are sound, and in fact MET.**
- UI-038: the spec now names the zero-JS static map "a conforming default" (spec:5950), and the
  tests cover it. The matrix still cites the deleted `reference-map.astro`.
- UI-047: the MapLibre island is built (P27, ADR-097) and its three if-shipped conditions are
  tested.

Neither is a deviation any more.

**Family bookkeeping defects:**
- CAPSTONE_CLOSURE §(b) says "76" rows; the matrix has 77.
- The SIG-ENG-005 row cites ADR-041 (the records-request generator).
- SIG-METRIC-011 (MET) and SIG-INGEST-029 (MET) state the same obligations as CHART-034 and
  CHART-033, and need the same re-verdict. They are outside F2b's scope.

---

## 5. Findings raised (`findings/incoming/F2b.csv`)

| f_id | sev | title (short) | routed |
|---|---|---|---|
| NEW-1 | **S1** | 75-row MET-DIFFERENTLY family is a prefix default (65 rows); sample ≈ half not met | F2; T4; B4 |
| NEW-2 | S2 | SIG-EPIS-009 derivation / independence guard inert at claim level | C3; F2; T4 |
| NEW-3 | S2 | EVAL-003/004 (MET) contradicted by operated auto-write and public report; EVAL-006 violated now | F2; F4; T4; C3 |
| NEW-4 | S2 | `check_coverage_matrix.py` in no gate; structure-only (refines F-27) | B4; T4 |
| NEW-5 | S2 | contributor-safety.md claims legal-defence resources and a monitored contact path that do not exist | E2; T1; F1 |
| NEW-6 | S2 | owed human/operator legs with no DEFERRALS row (UI-042, GOV-012/013/015, SEC-003, production Zenodo, geographic mirror) | F1; T4 |
| NEW-7 | S3 | keepalive never executed; first run 2026-10-01T07:00Z | G1; G2 |
| NEW-8 | S2 | leverage measures: 1 of 6 exists, yet CHART-034 and METRIC-011 read met | J3; T4 |

These refine, and do not duplicate, F-16, F-27 and F-30, A3 NEW-1, E1 NEW-1/5/7/8/10/12/14, E3
NEW-1/2/4/5/7/8, E4 NEW-7/8, G1 NEW-4 and J1 NEW-1/4/12.

## 6. Decisions to put to the operator (S5)

1. Adopt the vocabulary: add MET-ENGINEERED and WAIVED, add the four columns, and apply the
   validator changes.
2. The Stage-0 waiver ADR (5 rows).
3. Legal home, editorial board and legal-defence resources: constitute or obtain them, or record
   WAIVED ADRs. Neither can stay silently asserted in public docs.
4. Provisional auto-write under EVAL-004: demote now, or record a WAIVED ADR with a revisit trigger.
5. Whether T4 re-verdicts all 75 MET-DIFFERENTLY rows, or only the 65 prefix-default rows, and who
   owns it.
