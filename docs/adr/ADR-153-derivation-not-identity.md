# ADR-153: Derivation, not identity

- **Status:** Accepted
- **Date:** 2026-10-01T04:43:37Z (decided by the operator at GATE-P — the later of this ADR's two lines: B-31, log round 15, which enabled C2; the waiver itself is A-6, log round 3, 2026-10-01T04:03:25Z)
- **Phase:** Round 11 / Stage B seed (T1)
- **Ticket:** SEED-11 (unit SEED-11a)
- **Decided by:** the operator at GATE-P (`docs/build/planning/2026-09-30-next-phase/feedback/RATIFICATION_LOG.md`):
  - **A-6** (log round 3, 2026-10-01T04:03:25Z) — question *"evaluation: supersede rows 184–187; auto-merge only C0–C2;
    waive SIG-EVAL-004 lower bound for C0–C2"*; options "Adopt waiver sentence (Recommended) · No waiver"; answer
    **"Adopt waiver sentence (Recommended)"**, adopting the sentence quoted in full under Decision. Decision-catalog
    members answered: Q-L3-1 (a: derivation, not identity; auto-collapse only C0–C2; SIG-EVAL-004's lower bound waived for
    C0–C2), Q-24 (a: no certification attempt; no "human-verified", "certified" or camera-match-precision claim), Q-F4-1
    (answered by Q-L3-1 a).
  - **B-31** (log round 15, 2026-10-01T04:43:37Z) — question *"per-Class-S maintainer check; no in-round second model
    family; public `/quality/`; C2 enabled"*; options "As stated (Recommended) · No maintainer check · C0/C1 only"; answer
    **"No maintainer check"**. The selected option kept C2 (the alternative "C0/C1 only" was not chosen); the log's labelled
    interpretation records Q-L3-6 = a, "C2 enabled".
- **Requirement ids:** SIG-EVAL-004 — **WAIVED(ADR-153) for C0–C2 only** (waiver note at T1, plan §6.3); SIG-IDENT-028 —
  amended: auto-demotion for copy tiers is census-driven (plan §6.3); draft SIG-CONF-D04 (derivation, not identity), D05
  (identity inference never auto-written without independent evaluation), D14 (declared lineage, SHOULD) → SIG-CONF-0nn with the same numbers (SIG-CONF-D01 → SIG-CONF-001 …) in SEED-12's id map `PD/stageB/T1_id_map.csv`, read at writing (SEED-12 owns the final ids). Related, unchanged: SIG-IDENT-020 (tiers 0–3 may
  auto-write), SIG-EPIS-009, SIG-EPIS-029, SIG-RECON-018.
- **Spec:** §55.4 (SIG-EVAL-004 waiver note, C0–C2), §14.7 (SIG-IDENT-028 amendment); proposed Part XII §56 for the
  SIG-CONF drafts (SEED-12).
- **Supersedes:** **ADR-105 §5** (the measured auto-write gate on the agent- and maintainer-verified holdout, for camera
  sites) (plan §7 row 153; L3 ADR-L3-B).
- **Amends / qualifies / extends:** **amends ADR-099 §3** (the 0.98 floor applies only to independently evaluated tiers;
  inferential tiers no longer auto-write on a holdout measured from agent labels). The appended `Superseded by ADR-153`
  (ADR-105 §5) and `Amended by ADR-153` (ADR-099 §3) status lines are written by SEED-11d, not here.
- **Sources:** plan §5.4, §6.3 (SIG-EVAL-004, SIG-IDENT-028), §6.5 (SIG-EVAL-004 waiver row), §6.6 (F2b and L3 bullets),
  §4.2 A-6, §4.4 B-31, §7 row 153; `PD/design/L3-confidence-program.md` §0 item 6, §4.2 (M-1, M-1b, M-3, M-5), §4.6,
  §5.2, §6.2, §6.4, §7 (D04, D05, D14) and ADR-L3-B (§8); landed ADR-099 §3–§4 and ADR-105 §3–§6; spec SIG-EVAL-004
  (`docs/2_canonical_design_spec.md:7325`); `PD/data/round11_plan.csv` rows P34.45, P35.25, P35.46, P35.47
  (`PD` = `docs/build/planning/2026-09-30-next-phase/`).
- **Recorded:** 2026-10-01T07:35:39Z by Claude Code (Opus 5.5), harness `claude-code/claude-opus-5-5/subagent` — agent-drafted
  record of the operator's decision; operator words quoted verbatim from `PD/feedback/RATIFICATION_LOG.md`.

## Context

ADR-099 §3 let deterministic tiers 0–3 auto-write against a measured precision floor (`auto_write_precision_threshold ≥
0.98`) on a frozen holdout bootstrapped from LLM and maintainer labels, explicitly provisional under `D-R6.1-EVAL` (§4).
ADR-105 §5 instantiated that gate for camera sites: candidate tiers 1g (shared upstream ref) and 3g (coincident point) auto-write
when they reach the 0.98 floor on the committed gold set's frozen, *agent/maintainer-verified* holdout; under rules v2, 1g
measured 70/70 and 3g 69/70, and the auto-write of 3g "rests on the agent-verified labels, and that is disclosed".

L2/L3 found that this gate does not establish what it claims:
- the holdout labels were made by an AI model, twice; the two label sets disagree on tier 3 (73/74 vs 58/74), and tier 3
  auto-wrote 4,693 pairs on the favourable one (L2 NEW-15); the latest run's auto-write pairs number 11,106;
- tier 1g compares bare `external_ref` strings with **no id namespace**, so equal row numbers from unrelated layers qualify
  (L3 NEW-1), and 3g treats sub-metre coincidence between *independent* sources like coincidence between mirrors;
- SIG-EVAL-004 (MUST) requires a preregistered lower confidence bound of at least 0.98 on strict precision for each
  authorised tier, from human ground truth; whether identifier/derivation tiers are in its scope is undefined (L3 NEW-2);
- no independent human labels exist or are planned in Round 11 (U-008, U-011; ADR-152).

L3 separates two kinds of statement. A **derivation** statement ("these rows are copies of one upstream record") is a
provenance fact that a program can verify; an **identity** statement ("these independently produced records describe one
physical device") is an inference only human ground truth can certify.

## Decision

The operator's words (A-6):

> *"I accept derivation, not identity, and waive SIG-EVAL-004's lower-bound clause for C0–C2 as ADR-L3-B describes."*

agent-drafted, adopted by the operator at 2026-10-01T04:03:25Z (GATE-P log round 3, line A-6, option "Adopt waiver sentence
(Recommended)"); sha256 `03c0a79ef3b87d08165f985f45bbc9bb18d9e88487fb95455bfbd4f4017cdd55` (UTF-8 text between the log's
italic quote marks; `printf '%s' "<sentence>" | shasum -a 256`; equal to S6 §5's value). "ADR-L3-B" in the sentence names
L3 §8's draft, which this ADR records.

1. **Ruleset v3 — automatic collapse only for mechanically verified copies.**

   | tier | rule | disposition | basis shown (agent-drafted) |
   |---|---|---|---|
   | **C0** duplicate target | the same layer ingested twice under one source (row- or byte-identical; ADR-116 duplicate-target lineage) | collapse (auto) | "same upstream layer ingested twice" |
   | **C1** shared namespaced id | the same value in a declared `id_namespace` of a declared lineage (`mirror-of` / `derived-from`), unique in both captures, within the measured copy tolerance | collapse (auto); census every run (GQ-23); quarterly id-resolution sample (M-1b) | "copy of <origin> record <id>, checked automatically" |
   | **C2** exact position within a documented lineage | lineage declared with documentary evidence **and** measured overlap ≥ 0.9; bijective within 5 m; within the M-3 copy tolerance; no attribute conflict | collapse (auto) — **enabled** (B-31, Q-L3-6 = a) | "position-matched copy of <origin> (layer is a republish; matched by location)" |
   | **P** possible duplicate | 3g across independent lineages; 1g without a namespace; 4g; 5g; soft conflicts; refused unions; shape alerts | **not merged**; a `possible_duplicate` link with distance and reason; stays in the review queue | "possible duplicate of <record>, <d> m away; not merged: SIG cannot prove it is the same camera" |

   Hard constraints stand (ADR-105 §4) and gain one: never collapse two records one origin publisher lists as distinct
   (GQ-25); never incompatible technology once typed; clusters ≤ 50 m and ≤ 6 members.
2. **A collapse is a derivation link, not an entity merge.** It is recorded as `derived_from` with lineage evidence and a
   shared site id, in a new append-only run; `merged_into` stays unwritten (ADR-105 §6). Because it is bijective and
   bounded by GQ-25, it can never yield fewer distinct records than the origin publisher lists, so its worst failure is
   over-counting.
3. **Identity inference is never auto-written** while no independent-human evaluation certifies its tier (GQ-24). Every
   inferential match is published as a possible duplicate with basis and distance, and affected counts are published as
   an **interval** ("N records · between A and B listed cameras"), never as "resolved sites".
4. **Census-driven demotion replaces holdout-driven demotion for copy tiers** (SIG-IDENT-028 amended). After every ER run
   GQ-23 checks 100 % of C1/C2 collapses; any failure demotes that lineage's collapse tier on the next run and alerts. M-1b
   samples n = 200 collapses per declared namespace quarterly against the origin record and reports p̂, the exact lower
   bound, n and the failures as a measured property of the copy link — never as a certification figure (plan §5.4, TS-10).
5. **SIG-EVAL-004 is WAIVED(ADR-153), scoped to C0–C2.** The B5 lower-bound clause is not applied to the derivation-collapse
   tiers. For every inferential tier the requirement is met fail-safe ("insufficient evidence … retains … review-only
   status"). **Accepted risk:** a declared namespace or lineage could be wrong. **Compensating controls** (plan §6.5; L3
   §6.2): census-verified copies only (GQ-23); the M-1b id-resolution sample; origin distinctness (GQ-25); inferential
   matches published as possible duplicates with intervals (GQ-24); the per-record basis block (L3 §5.2); append-only,
   reversible runs; no certification claim. `D-R6.1-EVAL` is annotated to remove EVAL-004 from its legs (its remaining legs:
   EVAL-001/002/005/007, IDENT-027/028); the waiver's revisit trigger gets one BL row (L3 §6.2, §6.4).
6. **Organisations.** §14.6 tier 0 (an exact shared authoritative identifier) and tier 1 (an established crosswalk from an
   authoritative registry) auto-link — the derivation-by-identifier analogue; tier 2 (normalised name + state + class) stays
   "possibly the same" (D-K2-7) unless its collision list is generated from an authoritative registry; Splink tiers 4–5
   stay review-only (SIG-IDENT-020).
7. **Sequence (plan §5.4; `round11_plan.csv`).** P34.45 (CONF-02, wave 0, on the S5-3 OM-20 list) re-runs ER under ruleset
   v3 with inferential tiers review-only, superseding the live run's 11,106 auto-write pairs append-only; until P35.46
   (CONF-07a: derivation collapse + possible duplicates, after P35.25's declared lineage and id namespaces) lands the
   collapse tiers, the public figure is "N records; possible duplicates shown, not merged". P35.47 (CONF-07b) publishes
   `site_id`, `copies[]`, `possible_duplicates[]` and intervals. Under A-20 these structural writes may change live-API
   answers before HG-11, disclosed by the basis label and a `/status/` notice.

## Consequences

- The published "resolved sites" figure is withdrawn in favour of an interval (L3 §4.6 illustrates ≈196,700–≈203,400 listed
  cameras from 227,335 records on the 2026-09-27 release — an inference that depends on the lineage declarations).
- The dedup that reaches the public becomes real (site ids and copies), and every copy carries a checkable basis.
- A new mirror family must declare its lineage (and, for C1, its id namespace) before it can collapse; an undeclared
  > 50 % overlap is held from publication (GQ-11, draft SIG-CONF-D14).
- Real duplicates between independent sources stay double-listed as possible duplicates — the conservative direction —
  until an independent evaluation exists.
- SIG-EVAL-004's verdict becomes WAIVED(ADR-153) with `accepted_scope` C0–C2 and no open leg; the coverage checker's
  "WAIVED only with an accepted ADR and no open leg" rule depends on the `D-R6.1-EVAL` annotation above (plan §6.4).

## Alternatives considered

- **Keep the provisional auto-write under a time-boxed waiver** (F4 Q-F4-1 ii): rejected — it rests on agent labels.
- **Demote everything, C1/C2 included** (the Q-L3-1 "no waiver" path): honest, but leaves the 10–13 % cross-layer
  double counting in every count; not chosen ("Adopt waiver sentence").
- **C0/C1 only** (B-31's third option): not chosen; C2 enabled.
- **Record EVAL-004 as MET-DIFFERENTLY** by reclassifying copies as "not auto-write": rejected as over-claiming; a skeptic
  could read it as a convenient carve-out, and under-claiming is the safer error (L3 §4.6).

## Revisit trigger

- **T-EVAL-IND** fires (an independent evaluation of an inferential tier becomes possible; ADR-152).
- Any proposal to auto-write an inferential tier (3g across independent lineages, 1g without a namespace, 4g, 5g).
- GQ-23 (the derivation census) fails for any lineage twice in a quarter.
- An M-1b id-resolution sample's lower bound for a declared namespace falls below 0.98 (L3 ADR-L3-B's trigger level — an
  internal revisit threshold, never published as a certification figure).
- A new source family whose copies carry no id namespace.
- The operator withdraws the waiver.
