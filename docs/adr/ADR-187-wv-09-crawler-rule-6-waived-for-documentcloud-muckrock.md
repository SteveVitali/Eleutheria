# ADR-187: WV-09 — crawler rule 6 ("ask first") waived for DocumentCloud/MuckRock only

- **Status:** Accepted
- **Date:** 2026-10-01
- **Ticket:** SEED-11 (Round-11 Stage B, T1 — unit SEED-11d)
- **Requirement ids:** SIG-INGEST-036 rule 6 (WAIVED for DocumentCloud/MuckRock only); rules 1, 3, 4, 5, 7 and 8 bind; SIG-INGEST-037 (this is an ADR-level crawler-policy decision; its counsel clause is waived by ADR-182)
- **Spec:** docs/2_canonical_design_spec.md §26 — SIG-INGEST-036 at lines 4472–4492, rule 6 at line 4490 (as built at `71e8bc83`; source `docs/research/_meta/spec_src/52_partIV_s23to26_connectors_parse.md`)
- **Decision:** the operator's answer to S6-F2 (waiver WV-09), 2026-10-01T06:05:22Z — `docs/build/planning/2026-09-30-next-phase/feedback/RATIFICATION_LOG.md`, round 24; with B-39 (04:49:27Z) and B-41 R2a (04:51:39Z)
- **Plan:** `docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md` §4.4 (B-39, B-41), §4.8 (S6-F2), §5.5, §6.3 (SIG-INGEST-036 row), §6.5 (WV-09 row), §7 row 187, §14 R-18
- **Related:** ADR-184 (the fetch envelope), ADR-168 (collection conduct; rule-7 register), ADR-182 (WV-07), ADR-171 (outreach timing); `design/S6-ratification-applied.md` §6 flag 2
- **Recorded:** 2026-10-01T07:45:36Z (`date -u`) by Claude Code (Opus 5.5), Stage-B sub-agent SEED-11d. Everything in this record except the quoted operator words is agent-drafted.

## Context

The operator chose to fetch DocumentCloud/MuckRock despite its "no data mining" terms (B-39 "Also fetch
DocCloud/Sourcewell"; B-41 R2a "Fetch, screened"). Rule 6 of the crawler-conduct policy requires SIG to ask first where
the compact is unresolved and the source is a small civil-society project — DocumentCloud/MuckRock is a non-profit
project — while U-011 forbids contacting anyone outside the project. S6 flagged the conflict (flag 2; plan §14 R-18)
and gated the connector's activation on the operator's answer; round 24 put it to the operator.

## Decision

### The operator's words

- **Answer to S6-F2, verbatim:** "Waive rule 6 for these (Recommended)" — round 24, 2026-10-01T06:05:22Z.
- **Adopted sentence — agent-drafted, adopted by the operator at 2026-10-01T06:05:22Z:**

  > I waive crawler rule 6 (ask first) for DocumentCloud/MuckRock; SIG fetches public pages only, gently, and honours any opt-out immediately.

  sha256 `94f061234c413bd4ec841b94255889a1944dc5edae1a1037deeab130d2621fb0` (`printf '%s' "<sentence>" | shasum -a 256`,
  recomputed by SEED-11d; equals the value S6b recorded in plan §4.8).
- **B-39, verbatim:** "Also fetch DocCloud/Sourcewell" — 2026-10-01T04:49:27Z; **B-41 R2a, verbatim:** "Fetch, screened
  (Recommended)" — 2026-10-01T04:51:39Z.

### The requirement and the clause waived

> 6. **Ask first** where the compact is unresolved and the source is a small civil-society project.

— `docs/2_canonical_design_spec.md:4490` (an operative rule of **SIG-INGEST-036 (MUST)**, "SIG MUST adopt and publish a
Crawler Conduct Policy binding on every connector", line 4472)

- **Waived:** rule 6, for DocumentCloud/MuckRock only.
- **Still binding on DocumentCloud/MuckRock:** rule 1 (identify — the project UA with its owned explanation page,
  P35.38a), rule 3 (rate-limit conservatively, with backoff), rule 4 (never circumvent access controls), rule 5 (prefer
  the offered channel — its documented unauthenticated API), rule 7 (honour opt-out immediately and record it) and
  rule 8 (cache; refetch rarely). Rule 2 follows GL-GATE-08 on every host (ADR-168).
- **Still binding on every other source:** rule 6 itself.

### Scope

The `documentcloud` source and its connector, row **P36.77** (DocumentCloud documents hosted by MuckRock): public
documents only. The waiver reaches no other civil-society project. Coverage: `WAIVED(ADR-187)` for rule 6, scoped to
DocumentCloud/MuckRock in `accepted_scope` (T4, SEED-14).

### Compensating controls

1. **ADR-184's envelope** in full: public, unauthenticated pages only; no logins, keys or circumvention; rate-limited;
   the project UA with its owned explanation URL; terms captured verbatim; the exposure disclosed; the Part VIII screen
   on every byte (S6/S7 free-text and incidental-name redaction) and ADR-185's persistence rule.
2. **Opt-outs at once.** Any opt-out from DocumentCloud/MuckRock or from an uploader is honoured immediately and
   recorded in the rule-7 register (P36.1a).
3. **Credit the uploader.** Every claim links the uploader's page on DocumentCloud.
4. **Activation only by the operator.** P36.77 lands `ingestion_permitted=false` and activates in Wave D (P37.54) only
   after the operator's HG-03 flip with ING-GO-D (OP-26).

## Consequences

- SIG fetches from a civil-society project without asking, against its terms; the exposure stays the operator's
  accepted risk under plan §14 R-18 (the rule-6 part of R-18 is resolved by this ADR).
- T4 records the verdict and a BACKLOG revisit row; SEED-15's `ADR_TRIGGERS.csv` carries this trigger.

## Alternatives considered

- **Link-only after all (option b).** DocumentCloud stays a link; E4-R2a reverts to decline; P36.77 stays dark. Not
  chosen.
- **Ask first.** Requires outside contact, excluded by U-011 (outreach is owed later-phase, ADR-171).

## Revisit trigger

Revisit — by a new ADR — when any of these happens:

- an opt-out, block or objection from DocumentCloud/MuckRock or from an uploader (honour it first);
- DocumentCloud/MuckRock changes its terms;
- the operator authorises outside contact (U-011 revisited; LATER-04) — rule 6 then applies again and SIG asks.
