<!-- Authored from the reviewed six-stream PLAN.json; planning is not execution evidence. -->
# HUMAN-H4 — Human development review and dossier semantic acceptance

- **Sequence:** 184 of 200
- **Phase:** Round 10 / S3
- **Kind:** human
- **Tag:** six-stream-round10
- **base_branch:** current checkout — the branch the previous ticket left checked out
- **Depends on:** P32.9, P32.10, P32.22
- **Gate status:** actual human development and dossier semantic review; never guessed past
- **Live stage:** human-only

## Goal

Human development review and dossier semantic acceptance. Deliver the bounded delta below against the actual landed predecessor, preserving prior decisions and explicit verification domains.

## Load (read these — do not re-read others)

- Root `AGENTS.md`, then the nearest package `AGENTS.md` for every touched package; `docs/tickets/DEFERRALS.md` before work.
- `docs/2_canonical_design_spec.md` Part 0, §3, Part VIII, and §55; the tail audits rather than re-owns implementation requirements.
- `docs/build/planning/2026-09-25-six-streams/DESIGN.md` shared contract and sequencing sections; `docs/build/planning/2026-09-25-six-streams/HANDOFF.md` activation rules.
- `docs/build/planning/2026-09-25-six-streams/PLAN.json` for exact dependency/ownership map; `docs/tickets/00_MANIFEST.md` remains chain order.
- `docs/build/planning/2026-09-25-six-streams/research/S3-human-evaluation.md` for evidence, field contracts, limits and negative cases relevant to this unit.
- `docs/build/planning/2026-09-25-six-streams/research/S3-human-evaluation.md`.

## In scope — deliverables

1. Operator assigns independent device-reference reviewers and a separate competent documentary semantic reviewer/adjudicator; records pseudonymous roles, rubric and approved effort budget.
2. Using P32.9 tooling and P32.22 repaired snapshot, complete training/pilot/calibration labels only; persist disagreements and insufficient evidence. These labels may inform candidate development and are excluded from the final confirmatory holdout.
3. Complete the fixed dossier rubric and material governance/contract/relationship semantic review; device-label expertise is not automatically legal/applicability expertise.
4. Record development label/snapshot digests, review limits, and unresolved gaps; release the development set to P32.22a without claiming a completed confirmatory evaluation.

## Out of scope

- Other contracts retain their implementation ownership. Consume shared schemas/functions; do not fork them to finish this unit.
- No source rights flip, human label, gate signature, outreach, publication, main integration or unapproved spend is inferred from this ticket.
- Do not rewrite landed ADR bodies, claim history, prior run evidence or the active plan without an appended scoped amendment.

## Acceptance criteria

- [ ] Actual humans, independent label/adjudication process and development partition provenance are recorded; no agent labels count as human. *(human)*
- [ ] Dossier semantic readout records scores, traced material assertions and unresolved applicability/execution issues. *(human)*
- [ ] No final confirmatory sample is drawn before P32.22a freezes the candidate and its eligible population; no pilot label is recycled as sealed test evidence. *(human)*
- [ ] Actual authority and date recorded in `docs/build/readouts/HUMAN-H4.md` and the ledger gate record; checkboxes stay unticked until then. *(human)*

## Exit criterion and blocked consumers

The signed/verified readout satisfies the exact criteria above. This marker has no implement-spec run. Never guess past it; a deferral or reduced-scope decision requires the operator’s explicit recorded choice. Engineering before this marker can complete with precise OPEN RETURN PASS obligations; that does not satisfy this exit criterion.
Direct consumers: P32.22a.

## Requirement IDs to satisfy and stamp in the PR

No new requirement ownership. Verify the referenced prerequisites and the round-wide obligations; do not double-own another ticket’s ids.

## Cross-cutting invariants

The manifest and canonical §3/Part VIII bind this ticket: evidence-first; qualified uncertainty; append-only corrections; no plate/trip/person ingestion; sensitivity and licence compartments; fail-closed source gates; no invented human work; no merge/tag/push-main. Public access withdrawals apply even to historical releases and rollback.

## Notes

Planning baseline: `0e57e6461d6a5db2e8e0042464750ce2ea65db5e`; engineering is not yet implemented by this packet. Reconfirm anchors at P32.1. This contract is one coherent change; independent human, source and publication prerequisites remain visible in the readouts and deferrals.
