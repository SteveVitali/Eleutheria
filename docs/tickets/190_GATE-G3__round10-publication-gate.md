<!-- Authored from the reviewed six-stream PLAN.json; planning is not execution evidence. -->
# GATE-G3 — Review the Round-10 public release and intake operation

- **Sequence:** 190 of 200
- **Phase:** Round 10 / S4
- **Kind:** gate
- **Tag:** six-stream-round10
- **base_branch:** current checkout — the branch the previous ticket left checked out
- **Depends on:** P32.23a, P32.24
- **Gate status:** HG-11; never guessed past
- **Live stage:** human gate

## Goal

Review the Round-10 public release and intake operation. Deliver the bounded delta below against the actual landed predecessor, preserving prior decisions and explicit verification domains.

## Load (read these — do not re-read others)

- Root `AGENTS.md`, then the nearest package `AGENTS.md` for every touched package; `docs/tickets/DEFERRALS.md` before work.
- `docs/2_canonical_design_spec.md` Part 0, §3, Part VIII, and §55; the tail audits rather than re-owns implementation requirements.
- `docs/build/planning/2026-09-25-six-streams/DESIGN.md` shared contract and sequencing sections; `docs/build/planning/2026-09-25-six-streams/HANDOFF.md` activation rules.
- `docs/build/planning/2026-09-25-six-streams/PLAN.json` for exact dependency/ownership map; `docs/tickets/00_MANIFEST.md` remains chain order.
- `docs/build/planning/2026-09-25-six-streams/research/S4-public-product.md` for evidence, field contracts, limits and negative cases relevant to this unit.
- `docs/build/readouts/GATE-G3.md`.

## In scope — deliverables

1. Present concrete immutable candidate, change/suppression summary, rights/Part VIII decisions, evaluation posture, measured costs and rollback.
2. Present intake operating owner, retention/abuse policy and actual availability; acknowledge still-unknown dossier fields.
3. Record operator HG-11 decision and any additional required source/exposure approvals explicitly.

## Out of scope

- Other contracts retain their implementation ownership. Consume shared schemas/functions; do not fork them to finish this unit.
- No source rights flip, human label, gate signature, outreach, publication, main integration or unapproved spend is inferred from this ticket.
- Do not rewrite landed ADR bodies, claim history, prior run evidence or the active plan without an appended scoped amendment.

## Acceptance criteria

- [ ] No unresolved public-safety/rights/unsupported-affirmation blocker or OPEN obligation scoped as required-for-publication remains. *(human)*
- [ ] Only actual operator decision signs the gate; absent/declined approval leaves candidate unpublished. *(human)*
- [ ] Three dossiers meet the fixed pilot rubric and independent semantic review, or the operator explicitly records a reduced/incomplete publication scope without claiming pilot completion. *(human)*
- [ ] Actual authority and date recorded in `docs/build/readouts/GATE-G3.md` and the ledger gate record; checkboxes stay unticked until then. *(human)*

## Exit criterion and blocked consumers

The signed/verified readout satisfies the exact criteria above. This marker has no implement-spec run. Never guess past it; a deferral or reduced-scope decision requires the operator’s explicit recorded choice. Engineering before this marker can complete with precise OPEN RETURN PASS obligations; that does not satisfy this exit criterion.
Direct consumers: P32.25.

## Requirement IDs to satisfy and stamp in the PR

No new requirement ownership. Verify the referenced prerequisites and the round-wide obligations; do not double-own another ticket’s ids.

## Cross-cutting invariants

The manifest and canonical §3/Part VIII bind this ticket: evidence-first; qualified uncertainty; append-only corrections; no plate/trip/person ingestion; sensitivity and licence compartments; fail-closed source gates; no invented human work; no merge/tag/push-main. Public access withdrawals apply even to historical releases and rollback.

## Notes

Planning baseline: `0e57e6461d6a5db2e8e0042464750ce2ea65db5e`; engineering is not yet implemented by this packet. Reconfirm anchors at P32.1. This contract is one coherent change; independent human, source and publication prerequisites remain visible in the readouts and deferrals.
