# Run ledger — SEED-11c (Round 11 Stage B, T1): Round-11 ADRs 168–178 authored by SEED-11

- **Harness:** claude-code/claude-opus-5-5/subagent
- **Skills:** 4140fda
- **Started:** 2026-10-01T07:34:04Z
- **Closed:** 2026-10-01T07:44:56Z
- **Unit:** SEED-11c — write the Round-11 ADRs numbered 168…178 whose author in `PD/NEXT_PHASE_PLAN.md` §7 is SEED-11
  (`PD` = `docs/build/planning/2026-09-30-next-phase/`); brief `PD/stageB/AGENT_BRIEF.md`; Appendix A T1.
- **Worktree / branch:** `/Users/stevenvitali/Eleutheria-next-phase`, `r11/seed` (tip `f66b2450` when written; no git
  state changed by this unit — the planning orchestrator commits).

## What was done

| ADR | file | §7 author | decision recorded | relation to landed ADRs (§7) |
|---|---|---|---|---|
| 168 | `docs/adr/ADR-168-collection-conduct-gl-gate-08-re-confirmed-on-every-host.md` | SEED-11 | GL-GATE-08 re-confirmed "as is" (A-5, 04:03:25Z, against the recommendation) on every host per ADR-088 (round 26, 06:51:11Z); 046c reservations and rule-7 opt-outs built and honoured (P36.1a); owned UA contact page (P35.38a); `sig-project.org` not bought (B-6); INGEST-037 posture restated; RISK-P0-06 closes by it | **extends ADR-088** |
| 169 | `docs/adr/ADR-169-rights-basis-with-guardrails-gl-gate-07-re-confirmed.md` | SEED-11 | operator-accepted basis with guardrails (A-4/Q-E2-13 c); GL-GATE-07 re-confirmed in the adopted A-7 sentence (against the recommendation); E4-B1 a; X3, A-9, A-22 (delegated-review disclosure), B-33…B-41 incl. the round-26 record clarification (S6R-02) for R4a/R4b; flips executed by the operator (OP-26, S6R-17) | none named |
| 170 | `docs/adr/ADR-170-odbl-map-basis-the-operators-own-determination.md` | SEED-11 | per-compartment map kept; ADR-106's basis re-recorded as the operator's own determination (no counsel, no document) on the C-3 sentence (A-4/Q-E2-14 c) | none named (ADR-086/106 `Qualified by` is ADR-167's) |
| 171 | `docs/adr/ADR-171-outreach-timing-owed-later-phase-no-outside-contact.md` | SEED-11 | outreach, records-request sending, recruiting, contribution-back → owed later-phase, trigger "operator authorises outside contact" (B-6/Q-E2-12 a; U-011); not waived | none named |
| 172 | `docs/adr/ADR-172-product-direction-and-scope-d3-ratified.md` | SEED-11 | D3 ratified with D3-Q3 = b (A-17, against the recommendation); co-primary journeys; CHART-025 amended; tagline (C-4, against the recommendation); announce gate = D3 §5 as restated in plan §13.5 **and** REVIEW-R11 S0/S1 fixed or dispositioned (S6-F3, round 24) | none named |
| 173 | `docs/adr/ADR-173-acquisition-waves-and-capacity.md` | SEED-11 | one ING-GO per wave + the operator's flip list; US-first ordering with non-US kept (S5-4, against the recommendation); 40 GB cap, 25 GB pre-grow, temporary tier bump; Wave D in scope; US + AU keys after the alias (B-11, B-18, C-8, A-19) | none named |

**Skipped (ticket-authored per §7; not written here):** ADR-174 (P35.1a — scheduler of record; supersedes ADR-016's
scheduler clause and ADR-076's scheduling path, status lines appended by P35.1a), ADR-175 (P34.6 — production data
protection and restore drills; `Qualified by ADR-175` on ADR-081 appended by P34.6), ADR-176 (P36.13 — API exposure
posture), ADR-177 (P37.3 — evidence retention, B-14 365-day unlocked), ADR-178 (P34.18 — public identifier re-key, B-3).

Every SEED-11c ADR carries the ADR-145 header shape (`# ADR-NNN: <title>`, `- **Status:** Accepted`, `- **Ticket:**
SEED-11`), the decision date from the log's round times, a `Written:` stamp from `date -u`, an "Operator words recorded
(verbatim)" table with each answer's sha256 (`printf '%s' … | shasum -a 256`, the method S6 used; checked against plan
§4.8's WV-08 value) and the label "agent-drafted, adopted by the operator at <time>" where the words were agent-drafted,
the declined recommendation stated plainly wherever the operator chose against it, and a `## Revisit trigger` section.
No landed ADR was edited; no status line was appended (SEED-11d's); the ADR index was not regenerated.

## Checks

| check | command | result |
|---|---|---|
| ADR policy test | `uv run pytest tests/unit/test_policy_adrs.py -q` | **169 passed** (all ADR files present at the time, incl. sibling units'); `-k` on ADR-168…173: **6 passed** |
| index parse (read-only) | `bash scripts/docs/adr-index.sh --check docs/adr` | the six new ADRs parse: title, Ticket `SEED-11`, Status `Accepted` (README not written) |
| repo-docs detector (read-only) | `bash scripts/docs/check-repo-docs-freshness.sh .` | 430 docs, 0 broken refs (untracked new ADRs are outside its git-listed corpus; report at the script's default `/tmp/repo-docs-freshness.json`) |
| privacy scan | `grep -i` for the operator's name / e-mail over the six ADRs and this ledger | clean |

## Open issues (for the orchestrator)

1. **Unit-prompt vs §7 wording.** The prompt described ADR-170 as "E2-13 DB right with guardrails" and ADR-171 as "E2-09
   SEC-003 legal-demand posture, U-011". §7 governs and was followed: ADR-170 = ODbL map basis (E2-13); the DB-right
   guardrails are in ADR-169 (E2-11, Q-E2-13); the SEC-003 legal-demand posture is ADR-166 (E2-10, another unit);
   ADR-171 = outreach timing (E2-09, U-011).
2. **RISK-P0-06** closes by ADR-168 (plan §6.5); appending the closure to `docs/risk_register.md` / BL-001 is outside
   this unit — route to the unit that owns risk-register appends (T1/T4).
3. **`D-P30.3-COUNSEL`** reads DONE (2026-09-24, closed by operator attestation) in `docs/tickets/DEFERRALS.md`'s main
   table and OPEN in a later summary table of the same file — for T4/SEED-14 (noted in ADR-170).
4. **Requirement id typo in plan §6.3:** "SIG-CONTRIB-012/012a/013/030a" — the spec has no SIG-CONTRIB-030a; the id is
   SIG-INGEST-030a, and E2-09 also names SIG-INGEST-029 (both included in ADR-171). SEED-12 should use the right ids.
5. **Q-E2-13 option c** also named re-deciding the out-of-rule / counsel-flagged rows (`camreg_und_001`,
   `camreg_calgary_ab`, Lexington, MD iMAP); no row in `PD/data/round11_plan.csv` does it after A-7/A-8. Recorded in
   ADR-169 as a labelled agent observation; the orchestrator decides whether a row or an operator line is owed.
6. **E4-R4a/R4b catalog cells:** `recommendation` carries an S4c draft ("b — capture the terms; NOT flipped this round")
   that differs from B-41's text as presented; ADR-169 records the answer to the text as presented (log round 26
   clarification). T4/SEED-14 may annotate the catalog cell.
7. Sibling ADRs (e.g. 162–165) still held a `@@…@@` placeholder when this unit stamped its own files; they were not
   touched.
