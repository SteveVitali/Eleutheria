# F4 — The deferred human-evaluation spine (rows 184–187) and how Round 11 picks it up

Row **F4** of `META_PLAN.md` (Stage P, Wave 5; depends on E3 and B3). This is a design memo only. It is read-only
over the repo, with one public-page read of `https://surveillancegraph.org/methodology/`. Nobody was contacted and
no human work was done or simulated (P4). Every decision below belongs to the operator; the recommendations are the
agent's.

- Started 2026-09-30T17:40:16Z; written from 2026-09-30T17:51:30Z (`date -u`). Planning branch head `41ab9521`.
- Evidence classes (P1): `code` · `recorded-execution` · `live-read` · `inference`. Effort and cost figures come from
  E3 (`research/E3-human-work.md`) and keep E3's markers: **[ext]** means an external web estimate, **[est]** means a
  planning assumption. None of them are measured times (`docs/evaluation/measured-time-worksheet.md` §4 rule 1).
- Every file cited in §10 was read, as a whole file or through `grep`/`sed` slices. LEDGER.md was not opened (P13).

---

## 0. Bottom line

1. **Rows 184–187 cannot be re-entered as written.** Their new prerequisites would all be Round-11 rows, but the
   validator only accepts dependencies on earlier rows. Their downstream consumer, row 188 (P32.23a), has already run
   under the provisional scope. HUMAN-H4 is tied to a repaired snapshot that exists only as a fixture. It also bundles
   two unrelated reviews that need different people and have different blockers (§3). The manifest's promise that
   "a resume re-enters at row 184 in order" (`00_MANIFEST.md:5`) cannot be kept honestly. It has to be replaced by an
   appended amendment.
2. **The human work runs on a different clock from the chain.** Round 10's 40 engineering rows landed in about
   44 hours (P32.1 at 2026-09-27T03:17:46Z, P33.8 at 2026-09-28T22:45:44Z, per `git log`). The human spine needs about
   3–5 months (E3 §5). If a human marker sits in a linear chain, the chain either stalls or the marker gets deferred.
   That is the structural cause of the four deferrals so far. Round 11 must take the human work off the chain's
   critical path.
3. **Recommendation: Option B, staged.** Supersede rows 184–187 with re-scoped Round-11 rows (full list in §7):
   - two engineering tickets: a reviewer labelling surface on an isolated evaluation database, and an honest
     auto-write posture;
   - two **non-blocking** human markers: **HUMAN-H6**, a device-label development pilot, and **HUMAN-H7**, a dossier
     semantic and hostile-reader review against live-captured dossiers;
   - a confirmatory segment of four rows: freeze, then **HUMAN-H8**, then one evaluation, then a republish. It is
     **ratified in principle but seeded only when trigger T-EVAL-1 fires**. This follows the Round-9 Wave-B precedent
     at `00_MANIFEST.md:448`.

   If nobody is recruited, B falls back to C on its own. The engineering is still useful, and the MUSTs stay owed
   under an explicit trigger.
4. **Measurement (Q-24): "certify or disclose" on one tier.** Preregister **tier 1g only, n = 149, zero errors
   allowed**:
   - if all 149 pass, tier 1g is certified, but only for the frozen frame (SIG-EVAL-006);
   - if not, the result is still an honest published estimate with its exact interval, and the tier keeps the
     posture decided in advance.

   The re-verified arithmetic (§5): even at a true precision of 0.995, a single-tier n = 149 campaign passes only 47%
   of the time. With a 1% insufficient-evidence rate, that drops to about 11%. A two-tier design certifies both tiers
   only 2.5–16% of the time at p = 0.99–0.995. The pilot's measured labelability should decide between n = 149 and
   n ≈ 100 (measure only).
5. **Seats (Q-25).**
   - **The operator may hold, with disclosure:** custodian, method reviewer (plus an OSF preregistration), and one of
     the two hostile readers. The custodian and method-reviewer seats also need an ADR-recorded exception to the
     rules-author firewall (`training-pilot-packet.md` §5).
   - **Must be external:** both first-pass labelers, the dossier semantic reviewer, and preferably the adjudicator.
6. **Correction to E2-14's premise.** Production auto-write is **not** in shadow mode. The hosted camera-site run
   auto-wrote **2,337** decisions: 1,089 at tier 1g and 1,248 at tier 3g. They rest on an agent-verified holdout. Only
   the P32.10 gate is in shadow mode (F4 NEW-1). What the public site may claim therefore depends on a posture
   decision the operator has not yet been asked to make (Q-F4-1, §8).
7. **`nextTicket` at the Round-11 seed:** the first row of the production-safety-and-honesty wave (B3 option N1; S2
   picks the row). It is never HUMAN-H4 or any row in 184–187. Rows 184–187 get a `superseded-by…` token appended to
   their Gate cell. B3's V2 rule must also skip HUMAN markers that are carried as RETURN PASS rows (F4 NEW-3).
   Otherwise HUMAN-H6 and HUMAN-H7 would recreate the Round-10 stall.

---

## 1. Where the spine stands today (verified)

| fact | evidence | class |
|---|---|---|
| Rows 184 HUMAN-H4 → 185 P32.22a → 186 HUMAN-H5 → 187 P32.23 are in the chain table and have not been executed. The manifest says they were deferred "wholesale" and that "a resume re-enters at row 184 in order". The amendment is dated "2026-10-19" but was committed 2026-09-28T01:27:21Z (already in B1's register) | `docs/tickets/00_MANIFEST.md:5, :380-383`; `git log -S` → `a33cd6ec` | code, recorded-execution |
| Both readouts read `Status: PENDING. No human work or approval is asserted.` They were created by the Round-10 seed `d6c562e5` (2026-09-27T02:40:53Z) and have not changed since | `docs/build/readouts/HUMAN-H4.md`, `HUMAN-H5.md`; `git log` | code |
| The campaign marker is `tooling_ready`: 0 labels, 0 attestations, 0 adjudications. Its owner chain still names H4 → P32.22a → H5 → P32.23 | `docs/evaluation/human-campaign-marker-packet.md` §3 | code |
| HUMAN-H4 needs "P32.22 repaired snapshot". P32.22 shipped the application half **on the seeded fixture only**; "Production recovery has NOT run" | `184_HUMAN-H4…` deliverable 2; DEFERRALS `D-R10-LIVE-1` status cell (`DEFERRALS.md:582`) | code |
| Row 188 P32.23a, the consumer of P32.23, **has already run** under the amended provisional scope. Its candidate `p-17b713…` is proposed for supersession | `00_MANIFEST.md:5, :384`; `research/B1-date-drift.md` §5.8 | code |
| The Round-10 human-eval schema has never been deployed to hosted. `human_eval_campaign` (sqitch L48) sits on top of L44–L47. B1 records those as "very likely undeployed on hosted" (unverified, Q-B1-1). P32.9 ran with `live_verification=false` | `db/sqitch.plan:44-48`; `B1-date-drift.md:228-235`; `docs/build/runs/P32.9.md:11` | code, recorded-execution |
| Reviewers would need their own PostgreSQL login, the CLI and hand-edited JSONL workbooks. Hosted `sig-pg` allows 0 authorized networks | `docs/evaluation/reviewer-provisioning.md` §2; E3 NEW-2 | code |
| **Production auto-write is live under the PROVISIONAL policy.** The hosted run `camsite:13bedfe7…` made 2,337 auto-write decisions (tier 1g 1,089; tier 3g 1,248). Tiers 1 and 3 passed a point-estimate floor of 0.98 on a 180-pair agent-verified holdout (tier 1g 70/70; tier 3g 69/70 strict). The P32.10 `eval-confidence/1` gate is `mode="shadow"` and "the explicitly PROVISIONAL production policy … is untouched" | `docs/build/reports/p30.2b-hosted/resolution_scale.json` (`camera_site_run`); `resolution/src/resolution/camera_sites.py:1612-1641`; `resolution/src/resolution/data/camera_site_rules.toml:47`; `docs/evaluation/shadow-gate-readout.md` | recorded-execution, code |
| The public `/methodology/` page shows **both** the PROVISIONAL disclosure ("the gold set is LLM-bootstrapped …") **and** "P 1.000 · R 1.000 · F1 1.000 the frozen, human-verified holdout" | `curl https://surveillancegraph.org/methodology/` at 2026-09-30T17:42:43Z → 200 (text extracted in scratch, not committed) | live-read |
| The operator has not yet answered Q-8, Q-24…Q-28 or Q-D1-15…17 (time, money, people) | `feedback/OPERATOR_FEEDBACK.md` (U-001, U-002 only); `META_PLAN.md` §7 | code |
| F1 routes D-R10-HUMAN-1, D-R6.1-EVAL and D-P30.2b-2 to "human-marker(184…187, re-entered per F4)" | `data/owed_register_adjudication.csv:17, :21, :23` | code |

---

## 2. Preconditions before any H4-type human work can start (task 1)

"Removed by" names the Round-11 work or operator act that clears each blocker. The `EV*` ids are placeholders. T3
assigns the real row numbers (201+) and phase ids (P34+).

| # | blocker | evidence | removed by | gates |
|---|---|---|---|---|
| **PC-1** | **Reviewers cannot take part.** Each needs a personal PostgreSQL login, the CLI and hand-edited workbooks. There is no UI. A custodian may not import labels on a reviewer's behalf, because "the attestation is a claim made under the reviewer's own login" | `reviewer-provisioning.md` §2–§3; E3 NEW-2 | **EV1 — reviewer labelling surface** (§7.1): blinded packet rendering; per-reviewer authentication that writes **as** `sig_eval_reviewer` with `sig.eval_reviewer` set, so there is no proxying; an attestation step; timing captured into the worksheet; **no public route** (the `/curate/` lesson, F-02; G1 NEW-6 allow-list) | H6, H8 |
| **PC-2** | **No database reviewers can reach that holds the eval schema.** L48 depends on the undeployed Round-10 stack L44–L47. Hosted has 0 authorized networks. `sqitch verify`/`revert` defects (D-P32.10a-1, D-P32.16a-1) are open | `sqitch.plan:44-48`; B1; F5 scope | **EV1**, recommended form: an **isolated evaluation database** restored from the pinned frame snapshot with the full sqitch stack. No production exposure, and no wait for production Round-10 schema activation. Alternative: G2 activates L44–L48 on hosted and opens IAM-scoped reviewer access (Q-F4-2) | H6, H8 |
| **PC-3** | **No valid development frame for the pilot.** H4 is bound to P32.22's snapshot, which exists only as a fixture | `184_…` deliverable 2; `D-R10-LIVE-1` | **Design change, no new ticket:** draw the 40-item pilot from the *current* hosted camera-site run, as development-partition labels only. Record every pilot dependency group (entity, component, upstream lineage) as an exclusion list the confirmatory draw must honour (SIG-EVAL-001; `training-pilot-packet.md` §1). This removes the pilot's dependency on `D-R10-LIVE-1` | H6 |
| **PC-4** | **No stable confirmatory frame.** The frame must be the frozen candidate over the population it will govern. Round-11 hosted recovery (`D-R10-LIVE-1`), Stream-I camera ingests and the I1/C3 coordinate, jurisdiction and camera-type fixes all change the input mix and matching inputs. A frame frozen before them is stale when it arrives (SIG-EVAL-006 drift; SIG-EVAL-007) | spec `:7329`, `:7331`; META_PLAN §1 item 5; I1 incoming findings | The P32.22 **live pass** (G2/T3), the Round-11 camera-class ingest tickets, and the coordinate/jurisdiction/type fixes, named at T3 as the **frame-affecting set**. They are part of T-EVAL-1 (§7.2), not dependencies of H6 | confirmatory segment |
| **PC-5** | **The dossier review would be a review of stand-ins.** The three P32.18–20 dossiers are built over hand-authored stand-in documents | E3 NEW-3; `tests/connectors/fixtures/dossier/SOURCES.md` | The Round-11 **live return passes** D-P32.18-1, D-P32.19-1 and D-P32.20-1 (each after its E4 HG-03 per-target decision), plus E2-02's **dossier-build hostile-reader gate** ticket (the gate moves into the dossier build; the fixture review is removed, fix H-1) | H7 |
| **PC-6** | **The public baseline must be true while the campaign runs.** "Human-verified holdout" is live (F-06). Current claims do not name population, source mix or window (EVAL-006). The public report is not routed through the evaluator (EVAL-003). The auto-write posture has not been decided (EVAL-004) | live-read 17:42:43Z; F2b NEW-3 | **EV2** (§7.1), plus the first-wave honesty fixes H-4 and the EVAL-006 labelling, which R11-TRUTH owns. Not a technical prerequisite for H6, but a truth prerequisite for everything published while it runs | public claims |
| **PC-7** | **No people and no mandate** | Q-8, Q-24, Q-25, Q-28 unanswered | **Operator actions only; no ticket can remove this.** Q-28 authorizes outreach. Q-24/Q-25 fix the aim and the seats. Recruit 2 labelers plus 1 adjudicator/semantic reviewer (E3 R1, R2, R5). Record the firewall exception by ADR | H6, H7, H8 |
| **PC-8** | **No independent method check** | E3 R4 | Operator action: an OSF Registries preregistration (free, time-stamped) of the pilot design and, later, the confirmatory design [ext] | H8 |

Recruiting (PC-7) has a 2–6 week lead time [est] and is the longest pole. It can start as soon as Q-28 is answered,
while EV1 is being built, provided the invitation states a start date and no reviewer is provisioned before EV1 lands.

---

## 3. Why rows 184–187 cannot be re-entered as written

1. **Dependencies can only point backward.** The vendored validator checks "Depends on (backward only)"
   (`scripts/docs/check-build-memory.sh` §3). The spine's new prerequisites (EV1, the dossier live passes, the
   frame-affecting set) would all be rows 201+. Rows 184–187 either declare no dependency on them, which hides the
   coupling, or declare a forward dependency, which is a validator violation and an edit to a historical contract.
2. **Physical order controls execution** (`00_MANIFEST.md:3`). Re-entering at 184 after rows 2xx means `nextTicket`
   jumps backward. BUILD_INDEX would then land seq 184–187 after seq 2xx. That can be worked around, but it is not
   monotone, and B3's V2 rule assumes "lowest not-landed row".
3. **The downstream consumer has already been used.** P32.23 deliverable 2 says "final graph/release
   rematerialization belongs to P32.23a". Row 188 already ran under the provisional scope. A re-entered P32.23 has no
   rematerialization row after it, so a new row is needed either way.
4. **The contracts are bound to the wrong inputs.**
   - H4 is bound to a fixture-only snapshot.
   - All four cite the 2026-09-25 six-stream plan, "Sequence N of 200", planning baseline `0e57e64…`, and "Reconfirm
     anchors at P32.1".
   - P32.22a's gate requires a *combined* "HUMAN-H4 development/dossier readout".
5. **H4 couples two independent human tasks** (F4 NEW-9):

   | task | people | prerequisite | consumer |
   |---|---|---|---|
   | device-label pilot | R1/R2 | PC-1…PC-3 | P32.22a |
   | dossier semantic review | R5 | PC-5 | dossier `pilot_complete` and SIG-UI-042; **not** P32.22a |

   Keeping them together means live dossier captures block the device-label chain, even though methodology does not
   require that.

B3 reached the same conclusion from the ledger side: "in practice N2 becomes 'N1 with re-scoped rows placed first'"
(`design/B3-ledger-redesign.md` §3.12).

---

## 4. Options for the spine (task 2)

"Common honesty work" means the fixes every option needs: H-4 "human-verified" wording, EVAL-006 labelling of
current claims, EVAL-003 routing of the public report, the SIG-UI-042 fixture removal (H-1), and the Q-F4-1 posture.
Most of it is owned by R11-TRUTH. The human hours below are E3's per-role arithmetic; §4.4 shows how they are built.

### 4.1 Summary

| | **A — keep 184–187, re-enter in order** | **B — supersede, re-scoped rows (recommended, staged)** | **C — keep deferred with a trigger** |
|---|---|---|---|
| Manifest / LEDGER | 184–187 marked `deferred(D-R10-HUMAN-1; T-EVAL-A)`. `nextTicket` = row 201, then jumps back to HUMAN-H4 when the trigger fires. Contracts gain `> Amended` notes that re-scope them in all but name. A new rematerialization row is still needed | 184–187 marked `superseded-by…` (§7.3). New rows EV1, EV2, HUMAN-H6, HUMAN-H7. The confirmatory segment is seeded by `decompose-spec mode=extend` when T-EVAL-1 fires | 184–187 marked `deferred(D-R10-HUMAN-1; T-EVAL-C)`. No spine rows. An ADR records the fifth deferral and its trigger. When the trigger fires, it turns into B anyway (§3) |
| Human effort | **121–300 h**: both candidate tiers at 2 × 183 = 366 pairs [inference: the contracts leave n to P32.22a; `candidate_auto_write=[1,3]`] | **86–197 h** in total. 43–82 h in Round 11 (H6 + H7). 44–115 h after T-EVAL-1. Operator 28–61 h, externals 58–136 h | **0 h** |
| Cash (E3 rates) | $0 (volunteers) to ≈ $2.7k–13.3k all-paid [ext] | $0 to ≈ $1.8k–8.2k all-paid; mixed ≈ $1.2k–4.6k [ext] | $0 |
| Engineering | Hidden: EV1 is still needed but has no row. PC-4 and PC-5 are invisible in the chain | EV1 (1–2 tickets), EV2 (small). The rest is owned elsewhere (G2 live passes, Stream I, R11-TRUTH) | Honesty work only, **plus EV1**, or the trigger can never fire (§4.3) |
| Calendar | Starts only after every hidden prerequisite is met, then 3–5 months | Engineering takes days. Recruiting 2–6 weeks in parallel. H6 2–4 weeks. H7 2–6 weeks after live captures. After T-EVAL-1: freeze (days) → H8 4–9 weeks → evaluation (days). A human-verified figure is ≈ 3–5 months after recruiting starts [E3 est] | Indefinite |
| Public site may claim | Nothing new until P32.23, then per-tier certified or not certified | See §7.10. H7 → dossiers independently reviewed. H6 → a human development pilot measured labelability (no certification). The confirmatory result → tier 1g certified for frame F, or p̂ and a lower bound, not certified | The common honest-provisional set only, indefinitely |
| Main risk | Structural (§3); frames go stale from Round-11 ingests; the chain stalls at a marker again; 2-tier joint pass odds 2.5–16% at p = 0.99–0.995 | Recruiting may fail (then it degrades to C with the engineering already done); certification odds 22–86%; H6 and H7 need operator time (Q-E3-1) | Fifth deferral. The EVAL MUSTs stay contradicted in practice (E1-14). Auto-write keeps resting on model labels. Credibility cost with journalist and advocate readers (U-002) |

### 4.2 Requirement verdicts by option (F2b vocabulary, §8.3; proposal for T4)

"Now" means F2b's proposed current verdict. "+honesty" means after the common honesty wave, which applies to every
option.

| id | now | +honesty (any option) | A at completion | B at the end of Round 11 (H6 + H7 done, T-EVAL-1 not yet fired) | B at completion | C |
|---|---|---|---|---|---|---|
| SIG-EVAL-001 | PARTIAL | MET-ENGINEERED(D-R10-HUMAN-1) | MET | MET-ENGINEERED (pilot preregistered; confirmatory owed) | MET | MET-ENGINEERED |
| SIG-EVAL-002 | PARTIAL | MET-ENGINEERED once EV1 lands (reviewer access), else PARTIAL | MET | **MET** (real attested two-reader labels plus adjudication, recorded append-only) | MET | MET-ENGINEERED if EV1 is built, else PARTIAL |
| SIG-EVAL-003 | AT-RISK-INTEGRATION | MET (report routed through `evaluator.py`, with `unavailable` states) | MET | MET | MET | MET |
| SIG-EVAL-004 | AT-RISK-INTEGRATION | Depends on Q-F4-1: all tiers demoted → **MET** (fail-safe); retained → **WAIVED(ADR)**, time-boxed; hybrid → WAIVED(ADR) scoped to 1g | MET | as +honesty | **MET** (the gate ran on real evidence; a fail demotes or keeps the preregistered posture) | as +honesty |
| SIG-EVAL-005 | MISSING | MISSING → later-phase(T-EVAL-1) | MET | MISSING, owned by the seeded segment | MET | MISSING, later-phase(T-EVAL-C) |
| SIG-EVAL-006 | MISSING | PARTIAL (current claims labelled; the assessment-scoped leg is owed) | MET | PARTIAL | MET (scoped claim published) | PARTIAL |
| SIG-EVAL-007 | MISSING | MISSING | MET | MISSING | MET | MISSING |
| SIG-UI-042 (adjacent) | PARTIAL (F2b) | MISSING (fixture removed; E2-02) | MET after the H4 dossier leg | **MET-DIFFERENTLY(ADR)**: a real two-reader review of a live dossier, one reader being the maintainer, disclosed | same | MISSING |

The owners in the spec text, "Owner: P32.23" (`:7327`, `:7329`) and "Owner: P32.22a" (`:7331`), need an appended
owner re-home note at T1. **No requirement text changes and no waiver under B.**

### 4.3 Risks, stated plainly

- **A.** The operator's recorded promise ("re-enters at row 184 in order") would be kept in letter and broken in
  substance: the contracts would be re-scoped through amendments. The biggest practical risk is wasted human work. A
  confirmatory sample drawn before the Round-11 ingests and coordinate fixes is invalid under SIG-EVAL-007 the moment
  those land.
- **B.** Recruiting is the single point of failure. Even after the campaign, certification may fail. The design
  treats a failure as a publishable, honest measurement, not a loss (§5). The operator spends 28–61 h on the spine
  alone (E3's full MHP is 70–203 h, and the spine is only part of it). If the operator's weekly hours (Q-E3-1) are
  small, H6 and H7 should be placed after the production-safety wave.
- **C.** Without EV1, T-EVAL-C ("≥ 2 independent reviewers recruited") is practically unreachable. Nobody can
  volunteer for a workflow that needs a personal DB login and a terminal. C is only honest if it is written down as
  "human evaluation is not planned", with the MUSTs still owed and the site saying so.

### 4.4 Effort arithmetic (from E3 §2; per person unless noted)

- **R1 labeler.** Training 2–3 + pilot 5.3–10 + calibration 1–2, plus the final campaign at n × 4–12 min:
  - n = 100 → **15–35 h**;
  - n = 149 → **18–45 h**;
  - n = 236 → **24–62 h**;
  - n = 366 → **33–88 h**.
- **R2 adjudicator.** Training 2–3 + pilot 1.1–3.0, plus 20–30% of items at 8–15 min:
  - n = 149 → **7–17 h**;
  - n = 366 → **13–34 h**.
- **Fixed seats.** R3 custodian **16–33 h** (operator). R4 method reviewer **8–20 h** (operator).
- **Dossier review.** R5 semantic reviewer **12–23 h**. Hostile readers **7–14 h** in total, of which the operator's
  share is 4–8 h.
- **Totals.**
  - **A (n = 366):** 2 × (33–88) + 13–34 + 16–33 + 8–20 + 12–23 + 7–14 = **121–300 h**.
  - **B (n = 149):** 2 × (18–45) + 7–17 + 16–33 + 8–20 + 12–23 + 7–14 = **86–197 h**.
- **B split in time.**
  - **Round 11 (H6 + H7):** labelers 2 × 8.3–15; adjudicator pilot 3.1–6; custodian H4 share plus provisioning 4–9;
    R5 12–23; hostile 7–14. Total **≈ 43–82 h**.
  - **After T-EVAL-1:** labelers 2 × 9.9–29.8; adjudicator 4–11.3; custodian prep and QA 12–24; method reviewer 8–20.
    Total **≈ 44–115 h**.
- **Cash.**
  - Labelers at $25–40/h [ext].
  - The E3-person seat at $40–100/h [ext]. In E3 §5 this is the one external person who covers adjudication, the
    semantic review and hostile reader #1.
  - B all-paid: labelers $0.9k–3.6k + E3-person $0.9k–4.6k.
  - A all-paid: labelers $1.6k–7.0k + E3-person $1.1k–6.3k.
- **The evaluation database (EV1)** is an infrastructure cost for the campaign's duration. It is **not sized here**.
  The ticket sizes it against Q-10 and Q-23.

---

## 5. Measurement design: certify the 0.98 gate, or measure and disclose (task 3, Q-24)

**Re-verified arithmetic.** These are exact one-sided Clopper–Pearson bounds and exact binomial pass probabilities.
They were recomputed in this row with Python and no files written. The table reproduces E3 §4 except for one
clarification (F4 NEW-6).

| design | α per tier | smallest n (0 / ≤1 / ≤2 errors) | P(pass) at true p = 0.99 / 0.995 / 0.999 |
|---|---:|---|---|
| tier 1g only, n = 149, 0 errors | 0.05 | 149 / 236 / 313 | **0.22 / 0.47 / 0.86** |
| tier 1g only, n = 236, ≤ 1 error | 0.05 | — | 0.32 / 0.67 / 0.98 |
| tier 1g only, n = 400, ≤ 3 errors | 0.05 | — | 0.43 / 0.86 / 1.00 |
| tiers 1g + 3g, 183 each (Bonferroni) | 0.025 | 183 / 277 / 359 each | per tier 0.16 / 0.40 / 0.83; **both tiers 0.025 / 0.16 / 0.69** |

**Sensitivity to labelability.** `insufficient_evidence` and `unresolved` count as non-successes (SIG-EVAL-004;
`shadow-gate-readout.md`). Take a true precision of 0.995 on decisive pairs:

| insufficient-evidence rate | n = 149 | n = 236 | n = 400 |
|---|---:|---:|---:|
| 0% | 0.47 | 0.67 | 0.86 |
| 1% | 0.11 | 0.13 | 0.15 |
| 2% | 0.02 | 0.02 | 0.01 |

Labelability, not precision, decides whether certification is reachable.

**What an estimate-only design yields.**
- At n = 100 with all successes, the lower bound is 0.971.
- With 1, 2 or 3 failures it is 0.953, 0.938 or 0.924.
- Going from n = 100 to n = 149 costs about **8–23 h** in total (E3). That cost buys a chance of certification.

**Which tier.** This is inference from **model-made labels only**, a planning prior and not ground truth (P4). The two
agent label sets on the hosted holdout agree on **tier 1g**: 70/70 strict in both. They **disagree on tier 3g**:
69/70 strict from the gold verifier, but 56/70 strict from the LLM labels, with 13 insufficient and 1 non-match
(`resolution_scale.json` `tier_measurements` vs `tier_measurements_llm_labels`). Coincident-point pairs look much
harder to label. So tier 3g is unlikely to clear a gate that counts insufficient evidence as failure (F4 NEW-8).

**Recommendation: "certify or disclose", tier 1g, n = 149.**
- **Preregistration.** Preregister on OSF one hypothesis:
  - tier 1g strict precision has an exact lower bound ≥ 0.98, at α = 0.05;
  - fixed n and stopping rule;
  - the frame is keyed to the **source-mix frame digest**.
- **Consequences, fixed in advance:**
  - **Pass (149/149):** tier 1g auto-write is certified for that frame only. Newly ingested sources' pairs are
    *out of frame* and stay review-only until reassessed (SIG-EVAL-006 drift rule).
  - **Fail:** publish p̂, the exact lower bound and the labelability breakdown. Tier 1g keeps whatever posture Q-F4-1
    set: review-only, or provisional under its ADR. It is never promoted.
  - **Tier 3g:** no confirmatory hypothesis. It stays review-only or provisional per Q-F4-1. D-P30.2b-2's check
    ("tier-3g precision re-measured ≥ 0.98") remains OPEN with its own trigger.
- **Pilot decision rule (HUMAN-H6, development only).**
  - Stratify the 40 items so that at least 20 are tier-1g-type pairs.
  - If the pilot shows **any** `insufficient_evidence` on 1g-type pairs, or the median time per item is above
    12 min, switch the aim to **measure only (n ≈ 100)**. Alternatively, fix the packet evidence and re-pilot
    (`training-pilot-packet.md` §6).
  - Otherwise keep n = 149. Raise it to n = 236 only if the labelers commit the extra ≈ 12–35 h.
  - Caveat: 20 items is weak evidence. When the true insufficient rate is 2%, zero appear in 20 about 67% of the time.
- **Implication for the operator.** Certification is a coin flip at best, and only for one tier, one frame and one
  time window. The durable value is an honest, human-measured precision figure with its interval. The spec already
  permits that ("failed/inconclusive assessments retain provisional disclosures", SIG-EVAL-005). A new source mix
  triggers reassessment, so each Round-11 ingest wave shortens how long a certification stays valid.

---

## 6. Seat assignment (task 4, Q-25)

| seat | operator may hold? | condition | if not filled |
|---|---|---|---|
| R3 campaign custodian | **Yes** | Disclosed. An ADR-recorded exception to the `training-pilot-packet.md` §5 firewall (the custodian sees sealed labels before unsealing). Acceptable only because the freeze ticket pins the candidate first | No campaign |
| R4 method reviewer | **Yes** | Disclosed, plus an OSF preregistration as outside scrutiny. An agent may draft; it cannot sign (P4) | The freeze checklist stays unsigned |
| Hostile reader #2 (SIG-UI-042) | **Yes, as one of two** | Disclosed. The other reader must be external | No review; UI-042 stays MISSING |
| R2 adjudicator | Exception only | Preferred external. An operator adjudicator must record a blind vote before unsealing (`rubric.md` §5), which needs a firewall exception | Disagreements stay `unresolved`, which counts as a non-success (conservative, valid) |
| R1 first-pass labelers (×2) | **No** | The operator directed rule development. Absolute fallback: the operator plus **one** external reader, no adjudicator, an ADR exception, and the public statement "one reader is the project maintainer". This is weaker evidence (E3 §6) | The marker stays `tooling_ready` |
| R5 dossier semantic reviewer | **No** | Independence is required (`independent_semantic_review`) | Dossiers stay `not_run`; `pilot_complete=False` |
| Agents (any seat) | **Never** | May draft packets, preregistration and analysis code. May not label, attest, adjudicate, or sign a checklist or readout (P4; `reviewer-provisioning.md` §3) | — |

**Smallest staffing** (E3 §5): two external labelers plus **one** external person who serves as adjudicator,
semantic reviewer and hostile reader #1. The operator holds custodian, method reviewer and hostile reader #2. Q-28
(outreach authorization) comes before any of this.

---

## 7. Recommendation and its exact representation (task 5)

**Recommend B, staged.** Supersede rows 184–187. Seed EV1, EV2, HUMAN-H6 and HUMAN-H7 in Round 11. Ratify the
confirmatory segment in principle and seed it on T-EVAL-1. If T-EVAL-1 has not fired by the Round-11 acceptance, the
operator records the C posture by ADR, with trigger T-EVAL-0.

### 7.1 Round-11 rows (placeholders; T3 numbers them from 201 and places them per S2)

| placeholder | kind | replaces | depends on | gate / live stage | requirement ids | acceptance headline |
|---|---|---|---|---|---|---|
| **EV2** — honest auto-write posture and evaluation report | ticket | — (new; closes F2b NEW-3 and F4 NEW-1) | the R11-TRUTH wording tickets (H-4) | Q-F4-1 answered; live stage operator-gated: an ER re-run plus republish through the allow-listed path | SIG-EVAL-003, -004, -006 (labelling leg) | Eligibility follows the recorded posture (demote, or retain under ADR). The public report comes from `evaluator.py` output with `unavailable` states. The auto-write count, rule and label provenance are disclosed. No "human-verified" string remains (test pins its absence) |
| **EV1** — reviewer labelling surface and isolated evaluation database | ticket (T3 may split it EV1a/EV1b) | the missing prerequisite of 184 and 186 | P32.9, P32.10 (landed) | Q-F4-2 answered; live stage operator-gated: the evaluation DB is provisioned and the schema deployed; no public route | SIG-EVAL-001, -002 (engineering legs) | A reviewer can authenticate, attest, read a blinded packet and write `same`/`different`/`insufficient_evidence` with reasons and timing **as their own role**, without a terminal. The custodian cannot write labels (test). No model field is reachable. The route is absent from every public build (test). Proven with a **test campaign id** only; test rows never count (`human-campaign-marker-packet.md` §4). The living marker packet's owner chain is updated |
| **HUMAN-H6** — device-label development pilot | human (**non-blocking**) | 184 deliverables 1, 2, 4 | EV1 | Actual humans only. Development partition drawn from the current hosted run, with a pilot exclusion list (PC-3) | — (verifies 001/002) | Two attested independent readers on 40 stratified items, plus calibration. Measured insufficient rate and time per item. Exclusion-list digest recorded. The readout `HUMAN-H6.md` states the pilot decision rule's outcome (§5). **No certification claim** |
| **HUMAN-H7** — dossier semantic and hostile-reader review | human (**non-blocking**) | 184 deliverable 3; E2-02's scheduled review | the dossier live return passes (D-P32.18/19/20-1 tickets), the dossier-build gate ticket (E2-02) | Actual humans only; live-captured dossiers only | verifies SIG-DOS-002…005, SIG-UI-042 | 36-point rubric scores and material assertions traced to the fact-to-capture ledger, with unresolved issues recorded. Two hostile readers (one external, one the maintainer, disclosed), with every finding dispositioned. `review.status=completed` only from that record |

**Confirmatory segment: ratified in principle, seeded on T-EVAL-1.** Drafts are kept outside the chain until then
(Round-9 precedent). The ids are placeholders.

| placeholder | kind | replaces | depends on | requirement ids |
|---|---|---|---|---|
| **EV-F** — freeze the candidate and its confirmatory frame | ticket | 185 P32.22a | HUMAN-H6, the P32.22 live pass (`D-R10-LIVE-1`), the frame-affecting set (PC-4) | SIG-EVAL-007 (+001) |
| **HUMAN-H8** — blinded confirmatory campaign, tier 1g | human | 186 HUMAN-H5 | EV-F | — |
| **EV-D** — one evaluation, rules decision ADR, review-to-clustering check | ticket | 187 P32.23 | HUMAN-H8, EV-F | SIG-EVAL-005, -006 (+004) |
| **EV-R** — rematerialize and republish under the decision | ticket (or folded into the round's next scheduled republish) | the P32.23a role (188 already used) | EV-D | SIG-EVAL-006 (publication leg) |

### 7.2 Triggers

- **T-EVAL-1** fires when **all** of these hold, and is recorded in GATE DECISIONS with evidence:
  - (a) `HUMAN-H6.md` is signed and the pilot decision rule has been applied;
  - (b) the confirmatory seats are committed (≥ 2 independent labelers and 1 adjudicator attested on the evaluation
    database), or the §6 fallback is ADR-recorded;
  - (c) every row in the T3-named frame-affecting set has landed, **including the P32.22 live pass**;
  - (d) Q-24's aim is recorded.

  On firing: `decompose-spec mode=extend` seeds EV-F, HUMAN-H8, EV-D and EV-R as suffix-lettered inserts or next
  rows, with a Plan-extensions line.
- **T-EVAL-0** (time-box): if T-EVAL-1 has not fired by the Round-11 GATE-ACCEPT, the operator records one of the
  following in their own words:
  - **extend**, with a date; or
  - **C posture**: an ADR saying the EVAL MUSTs stay owed, the PROVISIONAL disclosure stays, and the revisit trigger
    is "≥ 2 independent labelers attested on the evaluation database".

  D-R10-HUMAN-1 stays OPEN either way. It is never closed, never WONTFIX, and never waived.

### 7.3 Manifest (append-only)

1. **A new dispatch amendment blockquote**, inserted after line 5. It removes nothing, and B2's guard treats it as an
   insertion. *Agent-drafted text:* "**Dispatch amendment — Round 11 human-evaluation re-scope (<`date -u`>,
   GATE-P).** Rows 184–187 are **superseded, not executed**: no human work, label or signature exists for them. This
   amendment supersedes the 'a resume re-enters at row 184 in order' sentence of the S3 deferral amendment above, and
   the 'Current' label of the Round-10 import amendment. Their obligations (D-R10-HUMAN-1, D-R6.1-EVAL) pass to
   Round-11 rows EV1, EV2, HUMAN-H6, HUMAN-H7 and to a confirmatory segment seeded on trigger T-EVAL-1 (see Plan
   extensions). HUMAN-H6 and HUMAN-H7 are non-blocking markers: the chain continues past them with RETURN PASS rows,
   per the GATE-P decision recorded in LEDGER GATE DECISIONS."
2. **Gate-cell tokens on rows 184–187.** The existing text is kept byte-for-byte and the token is **appended**. This
   is layout.md's sanctioned `superseded-by-split` chain-table mark, and B3's machine-readable V2 token:
   - 184 → `· **superseded-by-split(HUMAN-H6, HUMAN-H7)** (R11 seed <date>)`
   - 185 → `· **superseded-by(EV-F; seeded on T-EVAL-1)**`
   - 186 → `· **superseded-by(HUMAN-H8; seeded on T-EVAL-1)**`
   - 187 → `· **superseded-by(EV-D, EV-R; seeded on T-EVAL-1)**`

   The file column, Kind and scope stay unchanged, so the validator's ticket↔row rule still holds and the files are
   kept.
3. **`## Plan extensions`:** one appended line recording the supersession, the new rows, T-EVAL-1/0, and the
   placeholder → real id map. A second line is appended when T-EVAL-1 fires.
4. **New rows** in the Round-11 chain table, placed per S2:
   - EV2 goes in the production-safety-and-honesty wave;
   - EV1 goes early, because recruiting lead time dominates;
   - HUMAN-H6 immediately after EV1;
   - HUMAN-H7 after the dossier live passes and the dossier-gate ticket.

   Marker ids: the next free marker numbers (H6, H7, H8) at T3. The validator's `ID_RE`
   (`(HUMAN-H|GATE-G)[0-9]+`) forbids suffix letters on markers, so a split cannot be named `HUMAN-H4a`/`HUMAN-H4b`.

### 7.4 Contracts 184–187 (BM-TICKET-04)

Each contract gets an appended dated note, and nothing else changes: "`> Amended <date -u>: SUPERSEDED — not
executed. No human work, label or signature was produced under this contract. Successor: <ids> (manifest Plan
extensions <date>). Do not dispatch.`"

### 7.5 Readouts

- `HUMAN-H4.md` and `HUMAN-H5.md` each get an appended section, "Superseded <date> — not executed; the checkboxes stay
  unticked forever; successors HUMAN-H6/HUMAN-H7 (and HUMAN-H8 on T-EVAL-1)".
- New `HUMAN-H6.md` and `HUMAN-H7.md` readouts are created PENDING at the seed, in the same shape as the Round-10
  seed's readouts.

### 7.6 DEFERRALS (append-only annotations; obligation events via M3's tool, recorded-at = `date -u`)

- **D-R10-HUMAN-1:** "· **Round-11 seed (<date>) — owner re-homed:** HUMAN-H4→P32.22a→HUMAN-H5→P32.23 superseded (not
  executed) by EV1, HUMAN-H6 (pilot), HUMAN-H7 (dossier review) and the T-EVAL-1 segment (EV-F→HUMAN-H8→EV-D→EV-R);
  stays OPEN". The status lead token is unchanged, so no transition event is needed; an annotation event is recorded.
- **D-R6.1-EVAL:** the same annotation, plus the Q-F4-1 posture and its ADR.
- **D-P30.2b-2:** "tier-3g confirmatory measurement not in the tier-1g campaign; stays OPEN; trigger: a 3g
  hypothesis in a later campaign". D-P30.2b-1 stays operator-action (F1, R12). EV-D keeps P32.23's
  review-to-clustering verification (SIG-EVAL-005).
- **New rows (for T4, not F4):**
  - SIG-UI-042 owner → HUMAN-H7 (F2b NEW-6);
  - the ADR-recorded firewall exception, as a compensating-control row if the operator takes the R3/R4 seats.

### 7.7 LEDGER seed (T5) and V2

- **`nextTicket`:** `<row 201 = first ticket of the production-safety-and-honesty wave (S2)>`, not HUMAN-H4. Its
  comment reads `rows 184–187 superseded-by(…) (F4)`.
- `lastCompleted: P33.8`. `projectStatus: PAUSED` until GATE-B (B3 §3.4).
- **`returnPass`:** at the seed it lists no 184–187 ids. HUMAN-H6 and HUMAN-H7 join it when the chain passes them.
- **GATE DECISIONS (verbatim, at GATE-P):**
  - Q-24, Q-25, Q-28, Q-F4-1, Q-F4-2 and Q-F4-3;
  - the rule "HUMAN-H6/H7 are non-blocking; pass with a RETURN PASS row". This is the operator's explicit recorded
    choice that the markers' own text requires before the chain continues past them.
- **V2 amendment (F4 NEW-3; input to B4/M2).** `nextTicket` = the lowest chain row that is not landed and is **not**
  (a) marked `deferred(`, `superseded-by(`, `superseded-by-split(` or `unused`, and **not** (b) a HUMAN marker listed
  in `returnPass` under a GATE-P non-blocking rule. Otherwise the result is `DONE`.
- **T6 dry-run assertion:** the orient resolves `nextTicket` = row 201 and reports rows 184–187 as superseded,
  pointing at their successors.

### 7.8 BUILD_INDEX

B3 §3.11's "not-landed note" names 184–187 as **superseded (not executed)**, with pointers to the Plan-extensions
line. No rows are created for them.

### 7.9 Coverage (T4)

Apply the "+honesty" and "B at the end of Round 11" columns of §4.2 as they are earned. Re-home EVAL-005/007 owners
from P32.23/P32.22a to D-R10-HUMAN-1 until the segment is seeded, then to EV-D/EV-F.

### 7.10 What stays PROVISIONAL publicly until the spine runs

This list is the minimum truthful set. The wording is agent-drafted; the operator confirms it.

- **Resolution quality.** "Resolution thresholds and quality figures are measured against labels made by an AI model
  and checked by the same model family. No human has verified them. `<N>` automatic merges in the latest run (rule:
  `<tiers>`) rest on these provisional labels." N comes from the live report; it is 2,337 in the recorded hosted run.
  The wording must not use "human-verified" anywhere (F-06). It must name population, source mix and window
  (EVAL-006).
- **Dossiers.** "Not independently reviewed." Until HUMAN-H7, the hostile-reader review is described as "not yet
  performed" (E2-02 wording).
- **After HUMAN-H6 only:** "A 40-item human development pilot (two independent reviewers, <date>) measured
  labelability at `<x>`. This is development evidence and certifies nothing."
- **After EV-D:** exactly the preregistered scoped statement, pass or fail.

---

## 8. Operator decisions this design needs

The orchestrator assigns the final numbers (single writer).

| id | decision | recommendation | unblocks |
|---|---|---|---|
| Q-8 / Q-E3-1/2 | Human-work appetite: hours per week, cash ceiling | — (B needs 28–61 operator hours for the spine, $0 to ≈ $8k) | S2 placement of H6/H7 |
| Q-24 | Aim and tiers | **Certify or disclose, tier 1g, n = 149**; the pilot rule may switch to measure-only n ≈ 100 (§5) | EV-F preregistration |
| Q-25 | Operator seats | Custodian + method reviewer + hostile reader #2, disclosed, with an ADR firewall exception; adjudicator external (§6) | H6, H7, EV-F |
| Q-28 | Outreach to recruit reviewers (DeFlock / EFF-Atlas / MuckRock / academic) | Authorize at GATE-P, so recruiting overlaps EV1 | PC-7 |
| **Q-F4-1** (new) | Auto-write posture now: (i) demote tiers 1g and 3g to review-only; (ii) keep both provisional under a WAIVED(ADR); (iii) keep 1g provisional under the ADR and demote 3g to review-only | **(iii)** [inference from the agent label sets, §5]. Every option is honest if disclosed; the operator decides | EV2; EVAL-004 verdict |
| **Q-F4-2** (new) | Where reviewers write labels: an isolated evaluation DB restored from the frame snapshot, or hosted `sig-pg` after Round-10 schema activation plus IAM access | **Isolated evaluation DB** (no production exposure; no dependency on G2 activation) | EV1 |
| **Q-F4-3** (new) | Approve supersession of 184–187 (§7.3), which replaces the "re-enter at row 184" promise, and the non-blocking-marker rule | Approve | T3, T5 |

---

## 9. Findings raised (→ `findings/incoming/F4.csv`)

| id | sev | summary |
|---|---|---|
| NEW-1 | S2 | E2-14's premise is wrong. Production PROVISIONAL auto-write is live: 2,337 hosted decisions (1g 1,089; 3g 1,248). Only the P32.10 gate is in shadow mode |
| NEW-2 | S2 | Rows 184–187 cannot be re-entered "in order" as `00_MANIFEST.md:5` promises: dependencies may only point backward, row 188 has already run, and the snapshot is fixture-only |
| NEW-3 | S2 | B3's V2 `nextTicket` rule does not skip pending HUMAN markers carried as RETURN PASS rows (BM-LEDGER-03), so any Round-11 marker recreates the Round-10 stall |
| NEW-4 | S2 | Reviewer access on hosted first needs the undeployed Round-10 sqitch stack L44–L47 below `human_eval_campaign` (refines E3 NEW-2) |
| NEW-5 | S2 | Round-11 ingests and coordinate fixes invalidate any confirmatory frame frozen before them. Certification must be keyed to a source-mix frame digest |
| NEW-6 | S3 | E3 §4's two-tier pass probabilities are per tier. The chance both tiers certify is 0.025 / 0.16 / 0.69 |
| NEW-7 | S2 | The META_PLAN §11 change log is future-dated: commit `1b9b57b2` (17:39:46Z) wrote "20:05Z — B3 done". The planning ledger repeats F-21 |
| NEW-8 | S3 | The agent label sets disagree on tier 3g (69/70 vs 56/70 strict, 13 insufficient) and agree on 1g (70/70). Inference: target 1g only |
| NEW-9 | S2 | HUMAN-H4 bundles a device-label pilot and a dossier review, which have different people, prerequisites and consumers. P32.22a's gate needs the combined readout |
| NEW-10 | S2 | Clock mismatch: the Round-10 engineering chain ran about 44 h, while the human spine needs 3–5 months. A marker inside a linear chain stalls it; this is the structural cause of the four deferrals |

---

## 10. Evidence read, and limits

- **Planning.**
  - `META_PLAN.md` §1–§3, §6 (E/F/S/T rows), §7, §7.1, §8.1–§8.3 and §11.
  - `research/E3-human-work.md` (whole).
  - `design/E2-governance-options.md` §0, E2-02, E2-14…E2-16, §6 and §8.
  - `design/B3-ledger-redesign.md` §1, §2.6, §3.4, §3.11, §3.12, §5.2, §5.3 and §7–§8.
  - `research/F2b-verdicts.md` EVAL sections and §5–§6; `data/coverage_delta_F2b.csv` EVAL rows.
  - `research/B1-date-drift.md` §5.8 and sqitch.
  - `data/owed_register_adjudication.csv` rows 17, 20, 21, 23.
  - `feedback/OPERATOR_FEEDBACK.md`; `feedback/QUESTIONNAIRE.md` §E.
- **Tickets and readouts.**
  - `docs/tickets/184_…`, `185_…`, `186_…`, `187_…` (whole).
  - `00_MANIFEST.md:1-12, :336-398, :429-454`.
  - `DEFERRALS.md` rows D-R6.1-EVAL (status cell), D-R10-HUMAN-1, D-R10-LIVE-1, plus the D-P30.2b rows (grep).
  - `docs/build/readouts/HUMAN-H4.md`, `HUMAN-H5.md`.
- **Evaluation packet.** `docs/evaluation/*.md`: README, marker packet, shadow-gate readout, training/pilot packet and
  provisioning in whole; rubric §5; worksheet §4.
- **Code.**
  - `resolution/src/resolution/camera_sites.py:1612-1641`.
  - `resolution/src/resolution/data/camera_site_rules.toml:30-57`.
  - `eval_confidence.toml` (`mode`).
  - `db/sqitch.plan:38-50`.
  - `scripts/docs/check-build-memory.sh:140-260, :348-372`.
  - `docs/build/reports/p30.2b-hosted/resolution_scale.json`.
  - spec `:7319-7331`.
- **Skill.** `~/agent-skills/skills/build-memory/layout.md:60-80, :100-215, :225-310`.
- **Live.** `/methodology/` at 2026-09-30T17:42:43Z (200).
- **Git.** `a33cd6ec`, `d6c562e5`, `1b9b57b2`, and the P32.1 / P33.8 commit times.
- **Limits.**
  - Hosted sqitch state was not queried; L44–L48 being undeployed is B1's inference.
  - The 2,337 figure is the recorded P30.2b run; the current hosted run may differ.
  - All effort figures are E3 estimates, not measurements.
  - The tier-choice argument rests on model-made labels and is labelled as inference.
