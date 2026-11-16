# ADR-248 — Sqitch DDL is the authoritative physical schema; the generated `sig.sql` is documentation only (P37.58)

- Date: 2026-11-15
- Status: accepted
- Ticket: P37.58 (R11-DEBT-02, BL-049 — manifest row 486 — on `r11/P37.58-schema-conformance`)
- Base: `r11/P37.57b-whole-graph-audits`
- Requirement stamps: SIG-STORE-045 (the clause this ADR answers),
  SIG-STORE-041 (the sqitch lifecycle), SIG-STORE-034 + SIG-ENG-016 (the
  generation gate that keeps the artifact fresh), ADR-007 (LinkML is the
  single source of truth), RISK-P2-04 → BL-049, F3 NEW-10
- Decision implemented verbatim: `STORE-045 route decided at GATE-P (SEED-11)`
  (the plan cell — a ticket, not an adr-waiver: F2a chose `ticket(BL-049)`
  for SIG-STORE-045 over the LD-D01 waiver, BL-049 register row); the
  catalog's preferred shape lands: "Either a conformance test between
  generated DDL and deployed sqitch, or (preferred) the T1 ADR making sqitch
  DDL authoritative plus a test that the generated DDL is documentation
  only" (`ticket_catalog.csv` R11-DEBT-02).
- Supersedes: nothing
- Amends / qualifies / extends: qualifies SIG-STORE-045's "the shipped DDL is
  generated from the LinkML ontology; where the two differ, the generated
  artifact is authoritative" clause — for the *logical* schema the ontology
  stays authoritative (ADR-007); for the *physical* schema the sqitch chain
  is. The clause's reconciliation rule is unchanged: a divergence between
  Appendix C's specification and the deployed DDL is still a defect to
  reconcile, never a licence to hand-edit the database.

## Context

SIG-STORE-045 declares the shipped DDL generated from LinkML and the
generated artifact authoritative. What the repo actually does — and has
always done — is the other posture: the deployed physical schema is
hand-authored sqitch (`db/sqitch.plan` plus `db/deploy|revert|verify` per
change, SIG-STORE-041, the ADR-196 lifecycle), while the LinkML-generated
`ontology/generated/sql/sig.sql` (`SQLTableGenerator` logical DDL — generic
types, no triggers, no RLS, no exclusion constraints, no roles or grants) is
neither deployed nor compared. Nothing under `db/` references it; only the
generation gate (`tests/ontology/test_generation_gate.py`) keeps it fresh.
The records disagreed about whether that posture was debt or sanctioned:
open BL-049 (RISK-P2-04) recorded it as owed while accepted BL-050's LD-D01
recorded the same posture as a sanctioned deviation — F3 NEW-10's
contradiction. GATE-P routed it here as a ticket, whose catalog row names
this ADR the preferred close.

## Decision

1. **`db/sqitch.plan` is the sole authority for the deployed physical
   schema.** Every physical change is an authored sqitch change with its
   deploy/revert/verify scripts — the posture SIG-STORE-041 already enforces
   — because the spine's physical DDL carries epistemic machinery generated
   logical DDL cannot express: append-only triggers, sensitivity-tier RLS,
   the non-overlap exclusion constraint, roles and column-scoped grants.
2. **`ontology/generated/sql/sig.sql` is documentation only.** It is a
   §20.1 downstream form — the logical schema rendered as illustrative DDL —
   kept fresh by the generation gate (SIG-STORE-034 / SIG-ENG-016), and it
   self-declares the posture in a generator-written header so the artifact
   cannot be mistaken for a deploy script. The conformance test
   (`tests/unit/test_schema_conformance.py`) pins it: no deploy surface may
   reference it, and the plan's script set must stay complete.
3. **The BL-049 / BL-050 contradiction is reconciled on the sanctioned
   side.** BL-050/LD-D01 recorded reality; the open BL-049 debt is closed by
   recording the reality as the decided rule. SIG-STORE-045's verdict
   becomes MET-DIFFERENTLY(ADR-248): its intent — one schema authority, a
   named reconciliation rule, no hand-edited database — is fully met by the
   sqitch authority plus the pinned documentation-only posture.

## Alternatives

- **A generated-vs-deployed conformance test (the catalog's other leg).**
  Rejected: `sig.sql` is a *logical* surface — `SQLTableGenerator` emits
  CamelCase class tables, generic types (`DATETIME`, geometry as `TEXT`),
  and none of the physical machinery — so there is no sound mapping to
  assert, and an invented partial mapping would mint a contract the spec
  never wrote. The honest check is the pinned posture, not a false
  byte-level comparison.
- **The LD-D01-style adr-waiver (record and move on).** Rejected by the
  GATE-P route itself — F2a chose `ticket(BL-049)` over the waiver so the
  rule lands with its guard test, not as a further accepted deviation.
- **Generate the deployed DDL from LinkML.** Rejected: LinkML's SQL output
  cannot express the spine's enforcement machinery (append-only triggers,
  RLS, exclusion constraints, grants), and wiring the generator into the
  deploy path would make it a deploy tool — the opposite of fail-closed
  schema authorship.

## Revisit trigger

- A proposal to deploy, or diff-compare against, `sig.sql` — then this ADR
  is revisited, the real generated-vs-deployed contract is designed, and
  `test_schema_conformance.py` is replaced by that conformance check.
- The ontology generation stack gains physical fidelity (triggers, RLS,
  exclusion constraints, roles) — the generate-to-deploy question reopens
  with a mapping worth asserting.
- A second physical deploy authority appears under `db/` — the
  plan-sole-authority leg is revisited.
