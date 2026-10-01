<!-- Authored from the reviewed six-stream PLAN.json; planning is not execution evidence. -->
# HUMAN-H5 — Complete blinded confirmatory adjudication for the frozen candidate

- **Sequence:** 186 of 200
- **Phase:** Round 10 / S3
- **Kind:** human
- **Tag:** six-stream-round10
- **base_branch:** current checkout — the branch the previous ticket left checked out
- **Depends on:** P32.22a
- **Gate status:** actual independent confirmatory human work; never guessed past
- **Live stage:** human-only

## Goal

Complete blinded confirmatory adjudication for the frozen candidate. Deliver the bounded delta below against the actual landed predecessor, preserving prior decisions and explicit verification domains.

## Load (read these — do not re-read others)

- Root `AGENTS.md`, then the nearest package `AGENTS.md` for every touched package; `docs/tickets/DEFERRALS.md` before work.
- `docs/2_canonical_design_spec.md` Part 0, §3, Part VIII, and §55; the tail audits rather than re-owns implementation requirements.
- `docs/build/planning/2026-09-25-six-streams/DESIGN.md` shared contract and sequencing sections; `docs/build/planning/2026-09-25-six-streams/HANDOFF.md` activation rules.
- `docs/build/planning/2026-09-25-six-streams/PLAN.json` for exact dependency/ownership map; `docs/tickets/00_MANIFEST.md` remains chain order.
- `docs/build/planning/2026-09-25-six-streams/research/S3-human-evaluation.md` for evidence, field contracts, limits and negative cases relevant to this unit.
- `docs/build/readouts/HUMAN-H5.md`.
- `docs/build/planning/2026-09-25-six-streams/research/S3-human-evaluation.md`.

## In scope — deliverables

1. Independent reviewers label the fixed P32.22a sample with model/prior-label predictions hidden; preserve same/different/insufficient and missingness in the original denominator.
2. Complete independent second labels and adjudication with evidence under the frozen rubric; record deviations, blinding breaches and label corrections without overwriting history.
3. Seal final label watermark/digests, reviewer attestations and campaign completion. Transfer the unopened confirmatory set for P32.23 evaluation of the already-frozen candidate only.

## Out of scope

- Other contracts retain their implementation ownership. Consume shared schemas/functions; do not fork them to finish this unit.
- No source rights flip, human label, gate signature, outreach, publication, main integration or unapproved spend is inferred from this ticket.
- Do not rewrite landed ADR bodies, claim history, prior run evidence or the active plan without an appended scoped amendment.

## Acceptance criteria

- [ ] Signed readout identifies candidate, snapshot, sample and label digests; no unapproved extra draws, excluded failures or reused development labels. *(human)*
- [ ] Incomplete/missing/insufficient labels remain represented; actual human work is never supplied by agents; incomplete campaign does not satisfy the gate. *(human)*
- [ ] Actual authority and date recorded in `docs/build/readouts/HUMAN-H5.md` and the ledger gate record; checkboxes stay unticked until then. *(human)*

## Exit criterion and blocked consumers

The signed/verified readout satisfies the exact criteria above. This marker has no implement-spec run. Never guess past it; a deferral or reduced-scope decision requires the operator’s explicit recorded choice. Engineering before this marker can complete with precise OPEN RETURN PASS obligations; that does not satisfy this exit criterion.
Direct consumers: P32.23.

## Requirement IDs to satisfy and stamp in the PR

No new requirement ownership. Verify the referenced prerequisites and the round-wide obligations; do not double-own another ticket’s ids.

## Cross-cutting invariants

The manifest and canonical §3/Part VIII bind this ticket: evidence-first; qualified uncertainty; append-only corrections; no plate/trip/person ingestion; sensitivity and licence compartments; fail-closed source gates; no invented human work; no merge/tag/push-main. Public access withdrawals apply even to historical releases and rollback.

## Notes

Planning baseline: `0e57e6461d6a5db2e8e0042464750ce2ea65db5e`; engineering is not yet implemented by this packet. Reconfirm anchors at P32.1. This contract is one coherent change; independent human, source and publication prerequisites remain visible in the readouts and deferrals.

> Amended 2026-10-01: **Superseded — not executed** (2026-10-01T14:10:02Z; Stage-B unit SEED-13a; ADR-152; decided at GATE-P, A-6 "Adopt waiver sentence (Recommended)", 2026-10-01T04:03:25Z, with Q-L3-2 = a; L3 §6.3). No human work, label or signature was produced under this contract. Successor: `superseded-by(T-EVAL-IND segment: HUMAN-H8)` — the T-EVAL-IND rows are seeded only when T-EVAL-IND fires (plan §11.3), and CONF-02 / CONF-09 are Round-11 chain rows. Obligations `D-R10-HUMAN-1` and `D-R6.1-EVAL` stay OPEN, non-blocking. See `docs/tickets/00_MANIFEST.md` § Plan extensions (2026-10-01, "SUPERSEDE rows 184–187") and the Round-11 human-evaluation dispatch amendment at the top of the manifest.
> **Do not dispatch.**
