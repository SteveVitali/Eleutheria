# ADR-152: Confidence without independent review

- **Status:** Accepted
- **Date:** 2026-10-01T04:43:37Z (decided by the operator at GATE-P — the later of this ADR's two lines: B-31, log round 15; A-6 was answered in log round 3 at 2026-10-01T04:03:25Z)
- **Phase:** Round 11 / Stage B seed (T1)
- **Ticket:** SEED-11 (unit SEED-11a)
- **Decided by:** the operator at GATE-P (`docs/build/planning/2026-09-30-next-phase/feedback/RATIFICATION_LOG.md`):
  - **A-6** (log round 3, 2026-10-01T04:03:25Z) — question *"evaluation: supersede rows 184–187; auto-merge only C0–C2;
    waive SIG-EVAL-004 lower bound for C0–C2"*; options "Adopt waiver sentence (Recommended) · No waiver"; answer
    **"Adopt waiver sentence (Recommended)"**. Decision-catalog members answered: Q-L3-1 (a), Q-L3-2 (a: rows 184–187
    superseded; no Round-11 human rows; D-R10-HUMAN-1 OPEN, non-blocking, T-EVAL-IND), Q-24 (a: no certification attempt),
    Q-25 (a, later vacated by B-31), Q-E2-15 (c as re-planned by L3), Q-F4-1/2/3 (answered by Q-L3-1/2).
  - **B-31** (log round 15, 2026-10-01T04:43:37Z) — question *"per-Class-S maintainer check; no in-round second model
    family; public `/quality/`; C2 enabled"*; options "As stated (Recommended) · No maintainer check · C0/C1 only"; answer
    **"No maintainer check"** (chosen over the recommendation). Members answered: Q-L3-3 (c: no operator maintainer check;
    every Class-S readout and `/quality/` say "no human check performed"), Q-L3-4 (no in-round second model family),
    Q-L3-5 (yes: `/quality/` public, including failing and ratchet checks), Q-L3-6 (a: C2 enabled; recorded in ADR-153).
- **Requirement ids:** SIG-CONF-001 (basis classes), SIG-CONF-002 (agent labels segregated), SIG-CONF-003 (only mechanical
  checks gate), SIG-CONF-010 (maintainer checks disclosed, blind-first, verbatim — written "when performed"; Round 11
  performs none), SIG-CONF-011 (public quality page), SIG-CONF-012 (mechanical estimands labelled) — §56.7; drafted in
  L3 §7; final ids per `PD/stageB/T1_id_map.csv`; the §55.9 "Round-11 disposition" paragraph and the owner re-home notes on SIG-EVAL-005/006/007 (plan §6.3);
  SIG-EVAL-001/002/005/007, SIG-IDENT-027/028's independent legs, SIG-DOS-002's and SIG-UI-042's independent checks stay
  owed (not waived; plan §6.5).
- **Spec:** §55.4 (SIG-EVAL-001…007 owner re-home notes) and §55.9 (Round-11 disposition paragraph); Part XII
  §56.7 (SIG-CONF-001…003, SIG-CONF-010…012).
- **Supersedes:** none — no landed ADR (plan §7 lists none for this ADR). It supersedes the Round-10 manifest rows
  184–187 (`HUMAN-H4`, `P32.22a`, `HUMAN-H5`, `P32.23`) as records — superseded, not executed.
- **Amends / qualifies / extends:** none. ADR-099 §4 (`D-R6.1-EVAL`), ADR-128 and ADR-129 stand unchanged; their
  human-campaign revisit paths now wait on T-EVAL-IND (agent interpretation, labelled). Any appended status line on a
  landed ADR is written by SEED-11d, not here.
- **Sources:** plan §5.4, §6.2 (SIG-CONF row), §6.3 (SIG-EVAL-004; SIG-IDENT-028/§55.9/SIG-EVAL-005/006/007), §6.5, §6.6
  (L3 bullet), §4.2 A-6, §4.4 B-31, §7 row 152; `PD/design/L3-confidence-program.md` §0, §1, §4.1–§4.5, §5, §6, §7 and
  ADR-L3-A (§8); `PD/data/decision_catalog.csv` rows above; `PD/data/round11_plan.csv` rows P34.45, P35.48, P35.49
  (dropped), P37.44, P37.45, 184–187 (`PD` = `docs/build/planning/2026-09-30-next-phase/`).
- **Recorded:** 2026-10-01T07:35:39Z by Claude Code (Opus 5.5), harness `claude-code/claude-opus-5-5/subagent` — agent-drafted
  record of the operator's decision; operator words quoted verbatim from `PD/feedback/RATIFICATION_LOG.md`.

## Context

The operator said they are not confident in how disparate sources are synthesised into one deduplicated graph (U-006,
U-007), that there are no humans on the team besides them (U-008), and that no one outside the project is to be contacted
(U-011). L1 found the weakest seams at identity, export shaping, independence, schema mapping and evaluation; L2 measured
the copying layer as faithful (50 of 50 sampled sites reproduce their upstream record) and the synthesis as weak (5,278
collided subjects, 74.2 % with a publisher recorded as operator, 0 of 2.78 M evidence bindings reaching bytes, 29 of 45
metrics failing). F4's Option B — supersede rows 184–187 and seed an independent human-evaluation segment in Round 11 —
needs external labellers and recruiting, so it cannot run under U-008/U-011 (L3 §6.1). SIG-EVAL-001…007 and planning
principle P4 forbid substituting agent labels for human ones, yet the live site said "frozen, human-verified holdout"
(F-06/F-108) while the gold set was agent-adjudicated (ADR-105 §5).

L3 therefore drafted a program in which confidence is built by construction and held by mechanical checks, with every
quality statement carrying one basis class: **B0** by construction, **B1** mechanical census, **B2** mechanical sample
(exact interval), **B3** agent review, **B4** maintainer check (the operator; human but not independent), **B5**
independent human. B5 does not exist in Round 11. L3 proposed an optional B4 protocol (OPCHECK: 20 blind-first items per
Class-S release); the operator declined it at B-31.

## Decision

1. **Confidence by construction, held by a mechanical suite.** Round 11 builds the correctness prerequisites in L3 §2's
   order (CP-0 measurement substrate → CP-1 truthful claim identity → CP-2 subject keys → CP-4 declared lineage and
   independence, then CP-3/5/6/7/9/10 and CP-8 byte binding; plan §5.4 names the rows) and holds them with the
   graph-quality suite of ADR-154.
2. **Basis classes; only mechanical evidence gates.** Every published quality, evaluation or confidence statement carries
   exactly one basis class (B0–B5) plus n, population, source-mix digest, ruleset and window. Only B0–B2 (and, if it ever
   exists, B5 under SIG-EVAL-004) may gate a release, a materialization or an auto-write. **Agent evidence (B3) never
   gates**: it is recorded with labeller kind, model id, prompt digest and context id, kept out of `human_eval_*` tables
   (the ADR-128 roles already refuse it), never read by an auto-write gate, evaluation-status promotion or release gate,
   and never applied to partitions reserved for a future independent campaign. The agent review lane (P35.48) labels each
   item in two blind agent contexts; disagreement routes work, agreement is published only as "two AI runs agreed", never
   as accuracy. No second model family is used in-round (Q-L3-4).
3. **No human check this round (B-31).** There is no operator maintainer check (OPCHECK is not adopted; row P35.49 and
   OP-16/OP-17 are dropped) and the operator holds no evaluation seat (Q-25 vacated). **Every Class-S readout and the
   `/quality/` page say "no human check performed".** SIG-CONF-010 is written "disclosed when performed"; Round 11
   performs none.
4. **Independent evaluation is owed, not waived.** D-R10-HUMAN-1 stays OPEN, never waived and never WONTFIX, and is
   non-blocking: no Round-11 gate or row waits on a human marker. D-P30.2b-1 (curation decisions), which B-18 had folded
   into the maintainer check, has no fold target after B-31 and also stays OPEN, non-blocking (plan §4.4 B-18/B-31).
   Both re-open under **T-EVAL-IND**, which fires only when GATE DECISIONS records (a) the operator stating in their own
   words that at least two people independent of the project are available to label and authorising that contact (an
   explicit exception to U-011), (b) every frame-affecting prerequisite has landed, and (c) the Q-24 aim (L3 §6.5). On
   firing, `decompose-spec mode=extend` seeds F4 §7.1's segment (EV1 → HUMAN-H6 → EV-F → HUMAN-H8 → EV-D → EV-R; HUMAN-H7
   after the dossier live passes).
5. **Rows 184–187 are superseded, not executed.** No Round-11 human rows are seeded. Their non-human parts pass to P34.45
   (CONF-02: inferential tiers review-only, human estimands `unavailable`) and P37.44 (CONF-09: the mechanical evaluation
   report). T3 appends `superseded-by(…)` tokens to their gate cells; `HUMAN-H4.md`/`HUMAN-H5.md` gain "Superseded — not
   executed" sections (L3 §6.3).
6. **Verdicts (for T4; L3 §6.2 as answered).** SIG-EVAL-001 → MET-ENGINEERED(D-R10-HUMAN-1) once no surface claims a human
   leg; SIG-EVAL-002 stays PARTIAL; SIG-EVAL-003 → MET and SIG-EVAL-006 → MET once CONF-09/CONF-12 land; SIG-EVAL-004 →
   WAIVED(ADR-153) for C0–C2 only; SIG-EVAL-005/007 stay MISSING, owed, non-blocking (T-EVAL-IND); SIG-IDENT-027/028 →
   PARTIAL; SIG-IDENT-030 met by abstention (no centrality, ranking or hub statistic ships).
7. **Public wording.** Nothing anywhere says "human-verified", "independently reviewed", "verified" or "certified" without
   a B5 completion marker; L3 §4.5's not-claimable list holds in full (plan §5.4, TS-10), and P34.47 and P38.1a/b probe for
   it. `/quality/` (P37.45) renders every registered check — failing and ratchet checks shown (Q-L3-5) — from the
   release's `quality.json`, with a "who checked what" table whose maintainer-check and independent-review rows read none,
   and a "what we cannot tell you" section. The replacement text for "the frozen, human-verified holdout" (L3 §5.3) is
   agent-drafted and ships only after the operator confirms it verbatim (B-2); the honest posture ships in republish #1
   in its past-tense form (P34.17), the present-tense merge sentence with P35.63 (plan §5.4).

The operator's A-6 sentence, recorded in full in ADR-153 (which it names as "ADR-L3-B"):

> *"I accept derivation, not identity, and waive SIG-EVAL-004's lower-bound clause for C0–C2 as ADR-L3-B describes."*

agent-drafted, adopted by the operator at 2026-10-01T04:03:25Z (GATE-P log round 3, line A-6, option "Adopt waiver sentence
(Recommended)"); sha256 `03c0a79ef3b87d08165f985f45bbc9bb18d9e88487fb95455bfbd4f4017cdd55` (`printf '%s' "<sentence>" |
shasum -a 256`; equal to S6 §5's value).

## Consequences

- No "verified" wording remains on any surface; every readout and `/quality/` state "no human check performed", which is
  true and checkable.
- Journalists get a checkable method (named checks, populations and exact intervals) instead of a claimed one; the
  first releases after adoption show count intervals instead of "resolved sites" (ADR-153).
- The SIG-EVAL MUSTs stay visibly owed in DEFERRALS and the coverage matrix (MET-ENGINEERED / PARTIAL / MISSING with
  their D-ids), and GATE-ANNOUNCE lists them as owed for other reasons, not as waived (plan §6.5).
- Errors that only a human reader would catch are caught only by inbound corrections or not at all until T-EVAL-IND fires;
  the risk is accepted by the operator's B-31 choice and disclosed (plan §4.6 "no human checks").
- D-P30.2b-1's operator curation loop has no Round-11 path; possible duplicates stay in the review queue, shown but not
  merged (ADR-153).
- No spend: the agent lane runs in the executing harness; no second provider receives data.

## Alternatives considered

- **Amend the EVAL MUSTs into a "disclosed model-assisted standard"** (E2-14 a): rejected — it makes model agreement the
  standard for an evidentiary project (L3 ADR-L3-A).
- **Keep F4's Option B** (an in-round human-evaluation segment): infeasible under U-008 and U-011.
- **Waive all the EVAL MUSTs:** rejected — no operational gain, and it weakens the spec; EVAL-004 is waived only where
  Round 11 does what it governs (ADR-153).
- **A per-Class-S maintainer check (OPCHECK, the recommendation at B-31):** declined by the operator ("No maintainer
  check"); it would have been B4 evidence — disclosed, never independent, never gating.
- **A second model family for agent review:** declined (Q-L3-4) — metered spend, sends public data to another provider,
  and agreement would still not be accuracy. The post-round Claude Code review (REVIEW-R11, ADR-149) is a review of the
  build, not an evaluation of the data.

## Revisit trigger

- **T-EVAL-IND fires** (the operator records at least two available independent labellers and authorises that contact,
  with the frame-affecting prerequisites landed): seed the successor segment and write a new ADR for the evaluation.
- The operator changes U-008 (no humans besides the operator) or U-011 (no outside contact).
- The operator chooses to perform maintainer checks after all: a new ADR adopts a protocol under SIG-CONF-010
  (disclosed, blind-first, verbatim, never gating), and the "no human check performed" sentence changes only for the
  releases it covers.
- Any proposal to publish a precision figure for identity inference, or to let B3/B4 evidence gate anything.
- An inbound-correction pattern the mechanical suite did not catch: ≥ 3 confirmed errors of one class in one release.
