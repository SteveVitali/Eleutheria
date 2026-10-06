# ADR-179: WV-04 — SIG-UI-042's release block waived; the hostile-reader review is recorded "not yet performed"

- **Status:** Accepted
- **Date:** 2026-10-01
- **Ticket:** SEED-11 (Round-11 Stage B, T1 — unit SEED-11d)
- **Requirement ids:** SIG-UI-042 (its release-block clause WAIVED, scoped as below)
- **Spec:** docs/2_canonical_design_spec.md §41 — SIG-UI-042 at lines 5997–6001 (as built at `71e8bc83`; source `docs/research/_meta/spec_src/81_partVII_s39to41_ui.md`)
- **Decision:** the operator's answer to packet line A-23 part 2 (waiver candidate WV-04), 2026-10-01T04:28:49Z — `docs/build/planning/2026-09-30-next-phase/feedback/RATIFICATION_LOG.md`, round 9
- **Plan:** `docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md` §6.3 (SIG-UI-042 row), §6.5 (WV-04 row), §7 row 179, §11.3, §13.5
- **Related:** ADR-152 (confidence without independent review), ADR-163 (WV-03: single-maintainer publication posture), ADR-164 (WV-02: interim editorial authority and public decision log); `docs/risk_register.md` RISK-P15-29; plan §14 R-22
- **Recorded:** 2026-10-01T07:45:36Z (`date -u`) by Claude Code (Opus 5.5), Stage-B sub-agent SEED-11d. Everything in this record except the quoted operator words is agent-drafted.

## Context

SIG-UI-042 requires every dossier template version to pass a recorded two-reader **hostile-reader review**
before release, and blocks release until every finding is dispositioned. Round 11 has one human, the operator
(Q-8: no humans besides the operator; U-011: no outside contact), so no second, independent reader exists and none
may be recruited. The live `/editorial-standards/` page meanwhile showed a fixture review ("Reviewer A (counsel
stance); Reviewer B", "Releasable") that no reviewer ever performed, and the build gate `assertReviewReleasable`
throws unless two reviewer names are present, so a truthful record fails the web build (E1-02; E2-02 and its NEW-1;
`docs/build/planning/2026-09-30-next-phase/design/E2-governance-options.md` §E2-02).

S4's truth-and-safety review (TS-05) ruled that a spec amendment which weakens a MUST is a waiver and must be
decided in the operator's words. The packet therefore offered WV-04 at A-23 as "waive in your own words" or "keep
owed" (`data/decision_catalog.csv` row WV-04).

## Decision

### The operator's words

- **Answer to A-23 part 2 (multi-select; a tick waives), verbatim:** "WV-04 hostile-reader block (Recommended), WV-05
  anonymous intake (Recommended), WV-06 two-person deletion" — round 9, 2026-10-01T04:28:49Z.
- **Adopted sentence — agent-drafted, adopted by the operator at 2026-10-01T04:28:49Z:**

  > I waive SIG-UI-042's release block: releases may ship with the hostile-reader review recorded truthfully as 'not yet performed' and any findings listed as known issues.

  sha256 `2a0339a96d57e89015d0a7146116fa5b47e9966c4e13a9db76999a8d615f9c22` — `printf '%s' "<sentence>" | shasum -a 256`
  over the text between the log's italic quote marks, recomputed by SEED-11d; it equals the value S6 computed
  (`design/S6-ratification-applied.md` §5). The sentence was selected from an agent-drafted option, which the log
  records as the operator adopting it as their words (log round 24 note; plan §1.3).

### The requirement and the clause waived

> **SIG-UI-042 (MUST).** Each dossier template version MUST receive a recorded **hostile-reader
> review** before release: two reviewers independently read a real rendered dossier adopting the
> stance of the documented organization's counsel, log every sentence they would challenge, and sign
> off. The review, its findings, and their disposition MUST be committed alongside the template
> version. Release is blocked until every finding is dispositioned.

— `docs/2_canonical_design_spec.md:5997-6001`

- **Waived:** the release-blocking effect — "before release" (line 5998) and "Release is blocked until every finding
  is dispositioned." (line 6001). A dossier template version may be released while its hostile-reader review is
  recorded as not yet performed.
- **Not waived (agent reading of the sentence's scope, labelled):** what a hostile-reader review *is* when one is
  performed — two independent readers in the documented organization's counsel stance, every challenged sentence
  logged, sign-off, and the review, findings and dispositions committed alongside the template version. The review
  stays owed; nothing may present a review that did not happen.

### Scope

Every Round-11 release (Class R and Class S) and every dossier template version released while this ADR stands.
The coverage verdict is `WAIVED(ADR-179)` for SIG-UI-042, with `accepted_scope` naming the release-block clause
(recorded by T4, SEED-14; plan §6.6 and Appendix A T4).

### Compensating controls

1. **Truthful record.** `/editorial-standards/` states that the hostile-reader review has **not yet been performed**,
   shows no reviewer names, date or "releasable" verdict, and says the earlier fixture was an error (E2-02 option d
   wording, agent-drafted; confirmed verbatim in copy batch #1, B-2) — row **P34.17** (H-1).
2. **The gate stops failing on the truth.** The build gate is changed so a truthful zero-reviewer record does not fail
   the web build, and the fixture constant is removed (H-1 code change, P34.17).
3. **Findings as known issues.** Any finding raised against a dossier — from a reader report, the dispute channel or a
   later review — is listed on the known-issues page (**P36.49**) and in the next readout until dispositioned.
4. **No claim of adversarial review anywhere.** The Round-11 acceptance counts 0 counsel / board / independent-review
   claims without basis (plan §5.10 acceptance; the 11A live probe and P38.1).
5. **Disclosure in every readout.** Each Class S readout states "single maintainer, no second reviewer" (WV-03,
   ADR-163) and "no human check performed" (B-31, ADR-152).
6. **Announcement gate.** GATE-ANNOUNCE requires a keep/lift answer for WV-04 in the operator's words (plan §13.5;
   S6R-18).

## Consequences

- Dossiers can ship without an adversarial read. E2-02 states the exposure plainly: dossiers are what advocates carry
  into council meetings, and skipping the hostile read raises the chance that an overstatement reaches the
  organization it describes. That risk is carried as plan §14 R-22 (single maintainer with all eleven waivers).
- `docs/risk_register.md` RISK-P15-29 describes `assertReviewReleasable` as the release gate; once P34.17 moves the
  gate, that control text is historical. The register is append-only; its dated correction belongs to the T4
  register work (SEED-14), not to this ADR.
- T4 records the verdict and a BACKLOG revisit row for WV-04; SEED-15's `ADR_TRIGGERS.csv` carries this ADR's revisit
  trigger (plan §7 "Also at T1"; Appendix A T4).

## Alternatives considered

- **Keep SIG-UI-042 owed (option b at A-23).** Dossier releases would carry the open requirement on GATE-ANNOUNCE's
  "spec MUSTs unmet at launch" list. Not chosen.
- **Perform a real review now (E2-02 options b/c: the operator plus one external reader).** Needs a second, external
  reader; recruiting and outside contact are excluded this round (Q-8, Q-28, U-011).
- **Leave the fixture up.** Rejected by every option offered: it reads as a fabricated record (E2-02).

## Revisit trigger

Revisit — by a new ADR, never an edit of this one — when any of these happens:

- a hostile reader becomes available: a second maintainer, or the operator authorises outside contact (U-011
  revisited; LATER-04) so an external reader can be asked;
- GATE-ANNOUNCE: the operator records a keep/lift answer for WV-04 verbatim (plan §13.5, S6R-18);
- a documented organization, or its counsel, disputes a dossier sentence (the trigger E2-02 drafted for the waiver
  option).
