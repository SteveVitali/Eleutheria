# ADR-094 — Maximize publishable scope by evidenced rights resolution, never gate bypass

- **Status:** Accepted
- **Phase / ticket:** Phase 27 / P27.2 (`docs/tickets/P27.2__maximize-publishable-scope.md`) — design decision operator-ratified 2026-09-22; executed under HG-03/HG-02
- **Date:** 2026-09-22
- **Related:** ADR-085 (mandated-disclosure / derived-facts basis), ADR-086 (HG-02 counsel resolution — derived-facts publication compartment), the GL-GATE-07 mass-flip disposition (P26.16, `docs/build/LEDGER.md` § GATE DECISIONS), SIG-LIC-004 (the fail-closed export rights gate), §42/§42.3 (licensing, ODbL separation), Part VIII §0.7 + §43.4 (officer-naming). Evidence: `docs/build/reports/P27_LAUNCH_READINESS_PLAN.md` §1 (audit: 256,172 UNDETERMINED claims, ~99% `procurement`/`dot_511`/`france_belgium_procurement`).

## Context

The 2026-09-22 audit found **256,172 claims (24%) UNDETERMINED**, attributed by connector to
`procurement` (204,918), `dot_511` (34,650), `france_belgium_procurement` (14,462), and small tails —
overwhelmingly government / public-record material. The operator wants everything publishable. The
export gate (SIG-LIC-004) **fails closed** on UNDETERMINED, so the *only legitimate* way to publish is
to record a real, evidenced licence basis through the rights pipeline — **not** to weaken the gate.
Some source classes, however, carry Part VIII sensitivity and MUST NOT be flipped without review.

## Decision

1. **Evidenced per-connector rights review.** For each UNDETERMINED bucket, record a real licence
   basis through the rights pipeline (append-only new `rights_record` rows + source links), following
   the GL-GATE-07 disposition pattern: US public records → `LicenseRef-PublicRecord-FactualCompilation`;
   non-US operator data → `LicenseRef-OperatorAccepted-DBRight`; OSM-derived → `ODbL-1.0` (own
   compartment). Every basis carries a terms capture + reviewer + date.
2. **Compartments stay separated (SIG-LIC-004 / §42.3).** ODbL and share-alike are **never** relicensed
   permissive; they ship in their own compartments. `assert_separated` must still hold.
3. **Part VIII classes are held for operator sign-off.** `facial_recognition_world_map`,
   `pathways_rtcc_federation`, `pathways_acoustic_drone_location`, and anything person- or
   officer-naming (§43.4) are **not** auto-published — the reviewer prepares a packet; the operator
   ticks HG-03 (rights) / HG-02 (counsel). The default is no-publish.
4. **No bypass.** A source with no evidenced basis stays UNDETERMINED — a recorded gap, never
   force-published (the defining standard, §3.1; evidence-first).

## Consequences

- The publishable fraction rises toward ~100% of the non-sensitive bulk (procurement/dot_511/fr-be
  procurement become publishable on a real public-record basis), turning the national surface (ADR-090)
  from a fraction of the graph into most of it.
- The residue is a small, **named**, operator-gated set (the Part VIII classes) — honest, not hidden.
- The export gate remains fail-closed; nothing is published that the evidence does not support.

## Alternatives considered

- **Blanket-flip every source to a permissive licence.** Rejected — legally wrong for ODbL/share-alike
  (cannot be relicensed), unsafe for the Part VIII classes, and a violation of the evidence-first
  defining standard (§3.1). "All publishable" is achieved by *review*, not by weakening the gate.
- **Leave the 24% UNDETERMINED.** Rejected — it under-publishes a large body of legitimately-public
  government data the operator has directed us to surface.

## Proposed spec_src amendment (NOT applied — none required)

This is an **operational** disposition using the existing SIG-LIC-004 gate + the GL-GATE-07 / ADR-086
pattern; it mints **no** requirement id and needs **no** `spec_src` change. P27.2 records the gate
disposition (like GL-GATE-07) + this ADR's Appendix F row in its PR (SIG-ENG-039).

## Revisit trigger

- Counsel revises the public-record / factual-compilation basis, or a source's operator objects to
  publication — re-gate that source by a new ADR / gate decision.
- A held Part VIII class's sign-off changes (granted or withdrawn) — record the change as a new gate
  decision; never a silent flip.
- A new UNDETERMINED source class appears that does not fit the US-public-record / non-US-operator /
  ODbL taxonomy — extend the disposition by a new ADR.
