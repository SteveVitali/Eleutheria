# ADR-188: WV-10 — Flock transparency portals probe-only (SIG-INGEST-035's no-direct-capture clause waived)

- **Status:** Accepted
- **Date:** 2026-10-01
- **Ticket:** SEED-11 (Round-11 Stage B, T1 — unit SEED-11d)
- **Requirement ids:** SIG-INGEST-035 (no-direct-capture clause WAIVED for Flock transparency portals; aggregator-source and compartment clauses stand); SIG-INGEST-013, SIG-INGEST-036 rule 4 and SIG-INGEST-037 stand; SIG-LIC-004a
- **Spec:** docs/2_canonical_design_spec.md §23.4 — SIG-INGEST-035 at lines 4199–4202; §21.5 — SIG-INGEST-013 at lines 3518–3519 and the managed-challenge note at 3514–3515; §26 — rule 4 at lines 4486–4487 (as built at `71e8bc83`; sources `docs/research/_meta/spec_src/52_partIV_s23to26_connectors_parse.md`, `50_partIV_s21_connectors.md`)
- **Decision:** the operator's answer to S6R-01 (waiver WV-10), 2026-10-01T06:51:11Z — `docs/build/planning/2026-09-30-next-phase/feedback/RATIFICATION_LOG.md`, round 26; with A-17 (2026-10-01T04:16:29Z)
- **Plan:** `docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md` §4.2 (A-17), §4.6, §4.9 (S6R-01), §5.5 (Flock and Axon depth; vendor table), §6.3 (SIG-INGEST-035 row), §6.5 (WV-10 row), §7 row 188, §14 R-18
- **Related:** ADR-042 (the `flock_portal` aggregator connector, CC BY-SA compartment — unchanged), ADR-184 (the fetch envelope), ADR-168 (GL-GATE-08 on every host), ADR-182 (WV-07); `reviews/S6r-consistency.md` S6R-01, S6R-12
- **Recorded:** 2026-10-01T07:45:36Z (`date -u`) by Claude Code (Opus 5.5), Stage-B sub-agent SEED-11d. Everything in this record except the quoted operator words is agent-drafted.

## Context

A-17 chose to fetch vendor-hosted transparency pages (D3-Q3 b). SIG-INGEST-035 forbids direct capture from Flock,
whose every path returned a bot challenge to a scripted client (F2.1), and rule 4 / SIG-INGEST-013 forbid defeating a
challenge. S6r found the plan had scheduled a direct Flock portal connector (P36.74) against that unwaived MUST
(S6R-01). The operator was offered "Keep Flock via aggregator" (recommended) or "Waive 035; probe without
circumventing", and chose the waiver.

## Decision

### The operator's words

- **Answer to S6R-01, verbatim:** "Waive 035; probe without circumventing" — round 26, 2026-10-01T06:51:11Z (chosen over
  the recommendation "Keep Flock via aggregator").
- **Adopted sentence — agent-drafted, adopted by the operator at 2026-10-01T06:51:11Z:**

  > I waive INGEST-035's no-direct-capture clause; SIG may fetch Flock portal pages only when served without a challenge, and stops on any challenge.

  sha256 `82487f7b3f0d7aa6e0312f1c41649f2e19bdb654c462e31d19dab40482918fcf` (`printf '%s' "<sentence>" | shasum -a 256`,
  recomputed by SEED-11d; equals the value S6c recorded in plan §4.9).
- **A-17, verbatim:** "Ratify; fetch vendor pages" — round 6, 2026-10-01T04:16:29Z.

### The requirement and the clause waived

> **SIG-INGEST-035 (MUST).** This connector MUST source the portal layer from the **aggregator's
> public CC BY-SA 4.0 API** (§22.5, SC-18), and MUST NOT attempt direct capture from the vendor, whose
> every path returns a bot challenge (F2.1). Output MUST land in the **CC BY-SA 4.0 compartment**
> (SIG-LIC-004a), never merged into the CC-BY graph.

— `docs/2_canonical_design_spec.md:4199-4202`

- **Waived:** "MUST NOT attempt direct capture from the vendor" — for Flock transparency portals, and only in the
  probe-only form below.
- **Stand:** the aggregator-source clause — the Eyes on Flock aggregator remains the source of the portal layer
  (ADR-042; its share lists become organisation-level claims in P36.75) — and the compartment clause — any direct
  output lands in the CC BY-SA 4.0 compartment, never merged into the CC-BY graph (SIG-LIC-004a).
- **Untouched:** SIG-INGEST-013 ("MUST NOT operate a crawler that defeats a bot-management challenge on any source"),
  rule 4 and SIG-INGEST-037's anti-circumvention posture.

### The probe-only connector (row P36.74)

1. **One gentle probe per portal per run** under the project UA with its owned explanation page (P35.38a), rate-limited
   with backoff; further page requests to a portal only while it keeps serving without a challenge.
2. **Stop on any challenge.** A bot challenge, a 403 or an interstitial ends that portal's attempt and is recorded as a
   refusal with its kind. No challenge-solving, header spoofing, proxy rotation or browser automation.
3. **Known portals only (agent reading, labelled).** The probe set is the portals already known from the aggregator's
   inventory (I3 counted 917); this ADR adds no discovery method (§23.4 states SIG cannot discover portals by its own
   lawful means).
4. **What a served page yields.** A page served without a challenge is parsed with the Eyes on Flock mirror's portal
   schema, reconciled against the mirror, Part VIII-screened (ADR-185's persistence rule), its terms captured
   verbatim, and lands in the CC BY-SA 4.0 compartment.
5. **Expected yield today ≈ 0** (F2.1): the acceptance is a probe record — served or refused, with the refusal kind —
   for every portal attempted (plan §5.5 vendor table).
6. **Activation by the operator.** P36.74 activates in Wave B (P36.12) with ING-GO-B and the operator's flip list;
   robots per GL-GATE-08 (ADR-168); rule-7 opt-outs honoured at once (P36.1a).

### Scope

Flock transparency portals only, through P36.74. Coverage: `WAIVED(ADR-188)` for SIG-INGEST-035's no-direct-capture
clause, with the aggregator-source and compartment clauses keeping their own verdicts in `accepted_scope` (T4,
SEED-14).

## Consequences

- SIG sends probe requests to a vendor whose terms prohibit automated access; the residual exposure is a probe, not
  extraction (plan §14 R-18).
- If a portal is ever served, SIG gains per-agency retention, camera counts, aggregate search counts and shared-with
  lists directly; until then Flock depth comes from the aggregator and agency-side records.
- T4 records the verdict and a BACKLOG revisit row; SEED-15's `ADR_TRIGGERS.csv` carries this trigger.

## Alternatives considered

- **Keep Flock via the aggregator (the recommendation).** P36.74 would stay dark. Not chosen.
- **Defeat the challenge.** Never an option: SIG-INGEST-013 and rule 4 forbid it, and the operator's words say "stops on
  any challenge".

## Revisit trigger

Revisit — by a new ADR — when any of these happens:

- a portal is served without a challenge — the first non-zero yield: review the parse and the exposure before the
  output is published;
- a cease-and-desist, a block, or a terms or access change from Flock or an agency;
- an opt-out;
- the Eyes on Flock aggregator stops publishing (the portal layer's source).
